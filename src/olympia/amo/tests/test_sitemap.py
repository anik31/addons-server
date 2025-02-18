import datetime
import os
from collections import namedtuple
from unittest import mock

from django.conf import settings
from django.urls import reverse

from olympia import amo
from olympia.amo.sitemap import (
    AddonSitemap,
    AMOSitemap,
    build_sitemap,
    CollectionSitemap,
    get_sitemap_path,
    get_sitemap_section_pages,
    sitemaps,
)
from olympia.amo.tests import (
    addon_factory,
    collection_factory,
    license_factory,
    user_factory,
)

from .test_views import TEST_SITEMAPS_DIR


def test_addon_sitemap():
    addon_a = addon_factory(
        privacy_policy='privacy!',
        eula='eula!',
        version_kw={'license': license_factory()},
    )
    # addon_factory generates licenses by default, but always with a builtin >0
    addon_b = addon_factory()
    addon_b.update(last_updated=datetime.datetime(2020, 1, 1, 1, 1, 1))
    addon_c = addon_factory(
        eula='only eula', version_kw={'license': license_factory(builtin=1)}
    )
    addon_d = addon_factory(privacy_policy='only privacy')
    addon_factory(status=amo.STATUS_NOMINATED)  # shouldn't show up
    sitemap = AddonSitemap()
    assert list(sitemap.items()) == [
        (addon_d.last_updated, addon_d.slug, 'detail'),
        (addon_c.last_updated, addon_c.slug, 'detail'),
        (addon_a.last_updated, addon_a.slug, 'detail'),
        (addon_b.last_updated, addon_b.slug, 'detail'),
        (addon_d.last_updated, addon_d.slug, 'privacy'),
        (addon_a.last_updated, addon_a.slug, 'privacy'),
        (addon_c.last_updated, addon_c.slug, 'eula'),
        (addon_a.last_updated, addon_a.slug, 'eula'),
        (addon_a.last_updated, addon_a.slug, 'license'),
    ]
    for item in sitemap.items():
        assert sitemap.location(item) == reverse(
            'addons.' + item.urlname, args=[item.slug]
        )
        assert '/en-US/firefox/' in sitemap.location(item)
        assert sitemap.lastmod(item) == item.last_updated


def test_amo_sitemap():
    sitemap = AMOSitemap()
    for item in sitemap.items():
        assert sitemap.location(item) == reverse(item)


def test_collection_sitemap(mozilla_user):
    collection_a = collection_factory(
        author=mozilla_user, modified=datetime.datetime(2020, 1, 1, 1, 1, 1)
    )
    collection_b = collection_factory(
        author=mozilla_user, modified=datetime.datetime(2020, 2, 2, 2, 2, 2)
    )

    collection_factory(author=user_factory())  # not mozilla user
    sitemap = CollectionSitemap()
    assert list(sitemap.items()) == [
        (collection_b.modified, collection_b.slug, mozilla_user.id),
        (collection_a.modified, collection_a.slug, mozilla_user.id),
    ]
    for item in sitemap.items():
        assert sitemap.location(item) == reverse(
            'collections.detail', args=[mozilla_user.id, item.slug]
        )
        assert '/en-US/firefox/' in sitemap.location(item)
        assert sitemap.lastmod(item) == item.modified


def test_get_sitemap_section_pages():
    addon_factory()
    addon_factory()
    addon_factory()
    assert list(sitemaps.keys()) == ['amo', 'addons', 'collections']

    pages = get_sitemap_section_pages()
    assert pages == [
        ('amo', 1),
        ('addons', 1),
        ('collections', 1),
    ]
    with mock.patch.object(AddonSitemap, 'limit', 2):
        pages = get_sitemap_section_pages()
        assert pages == [
            ('amo', 1),
            ('addons', 1),
            ('addons', 2),
            ('collections', 1),
        ]


def test_build_sitemap():
    # test the index sitemap build first
    with mock.patch('olympia.amo.sitemap.get_sitemap_section_pages') as pages_mock:
        pages_mock.return_value = [
            ('amo', 1),
            ('addons', 1),
            ('addons', 2),
        ]
        built = build_sitemap()

        with open(os.path.join(TEST_SITEMAPS_DIR, 'sitemap.xml')) as sitemap:
            assert built == sitemap.read()

    # then a section build
    def items_mock(self):
        AddonValuesList = namedtuple('AddonValuesList', 'last_updated,slug,urlname')
        return [
            AddonValuesList(
                datetime.datetime(2020, 10, 2, 0, 0, 0), 'delicious-pierogi', 'detail'
            ),
            AddonValuesList(
                datetime.datetime(2020, 10, 1, 0, 0, 0), 'swanky-curry', 'detail'
            ),
            AddonValuesList(
                datetime.datetime(2020, 9, 30, 0, 0, 0), 'spicy-pierogi', 'detail'
            ),
        ]

    with mock.patch.object(AddonSitemap, 'items', items_mock):
        built = build_sitemap('addons')

        with open(os.path.join(TEST_SITEMAPS_DIR, 'sitemap-addons-2.xml')) as sitemap:
            assert built == sitemap.read()


def test_get_sitemap_path():
    path = settings.SITEMAP_STORAGE_PATH
    assert get_sitemap_path() == f'{path}/sitemap.xml'
    assert get_sitemap_path('foo') == f'{path}/sitemap-foo.xml'
    assert get_sitemap_path('foo', 1) == f'{path}/sitemap-foo.xml'
    assert get_sitemap_path('foo', 2) == f'{path}/sitemap-foo-2.xml'
