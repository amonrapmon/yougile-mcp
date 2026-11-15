"""Indalo server-rendered OAuth pages and redirect allowlist security tests."""

from __future__ import annotations

import unittest

from yougile_mcp.cloud import pages, redirects


class CloudPageTests(unittest.TestCase):
    def test_login_escapes_all_untrusted_values(self):
        attack = '<script>alert("boom")</script>'
        html = pages.login_page(
            action='/signin', hidden={'flow': attack, 'csrf': 'fixed'},
            heading=attack, lead='Подключение', error=attack, login=attack,
            client=(attack, attack),
        )
        self.assertNotIn(attack, html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('method="post"', html)
        self.assertIn('type="password"', html)
        self.assertIn('основа Indalo', html)
        self.assertIn('github.com/amonrapmon/yougile-mcp', html)

    def test_company_choice_escapes_id_and_title(self):
        html = pages.company_page(
            action='/signin/company', hidden={'flow': '<bad>'},
            companies=[('company-A', 'Alpha'), ('bad" onclick="alert(1)', '<script>')],
        )
        self.assertIn('company-A', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('" onclick="alert(1)', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('Выберите компанию', html)

    def test_message_page_escapes_text_and_links(self):
        html = pages.message_page('<bad>', 'Error <script>', link=('https://x/?a="', '<go>'))
        self.assertNotIn('<bad>', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;go&gt;', html)


class CloudRedirectTests(unittest.TestCase):
    def test_trusted_callbacks_and_loopback_allowed(self):
        extra = redirects.parse_allowed('https://chatgpt.com, cursor:')
        for url in (
            'https://claude.ai/oauth/callback',
            'https://chatgpt.com/connector/callback',
            'cursor://callback/path',
            'http://127.0.0.1:23456/callback',
            'http://localhost:1234/callback',
        ):
            with self.subTest(url=url):
                self.assertTrue(redirects.allowed(url, extra))

    def test_unsafe_callbacks_denied(self):
        extra = redirects.parse_allowed('https://chatgpt.com, cursor:')
        for url in (
            'https://chatgpt.com.evil.example/callback',
            'https://claude.ai.evil.example/oauth/callback',
            'javascript:alert(1)',
            'data:text/html,<script>',
            'https://unlisted.example/callback',
            'http://chatgpt.com/callback',
        ):
            with self.subTest(url=url):
                self.assertFalse(redirects.allowed(url, extra))

    def test_destination_is_human_readable(self):
        self.assertEqual(
            redirects.destination('http://127.0.0.1:3000/auth'),
            'программа на этом компьютере',
        )
        self.assertEqual(redirects.destination('https://chatgpt.com/oauth'), 'chatgpt.com')


if __name__ == '__main__':
    unittest.main()
