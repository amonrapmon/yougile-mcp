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
        self.assertNotIn('основа Indalo', html)
        self.assertIn('github.com/amonrapmon/yougile-mcp', html)

    def test_landing_has_github_avatar_mcp_url_and_no_upstream_footer(self):
        url = 'https://yougile.ooouch.com/mcp'
        html = pages.home_page(url)
        self.assertIn(url, html)
        self.assertIn('class="landing"', html)
        self.assertIn('class="landing-avatar"', html)
        self.assertIn('avatars.githubusercontent.com/u/167690761', html)
        self.assertIn('Исходный код на GitHub', html)
        self.assertIn('AGPL-3.0', html)
        self.assertNotIn('основа Indalo', html)
        self.assertNotIn('indalo-tech/yougile-mcp-cloud', html)
        self.assertNotIn('<script>alert(1)', html.lower())
        self.assertIn('aria-label="Скопировать адрес MCP-сервера"', html)
        self.assertIn('class="landing-copy"', html)
        self.assertIn('id="copy-status"', html)
        self.assertIn('<script src="/assets/landing.js" defer></script>', html)
        self.assertEqual(html.count('class="landing-step"'), 4)
        self.assertIn('04/', html)
        self.assertIn('Откиньтесь в кресле', html)
        self.assertIn('на стероидах.', html)
        self.assertIn('by Amonrapmon', html)
        self.assertIn('Claude Code', html)
        self.assertIn('Harness', html)
        self.assertNotIn('landing-protocol', html)
        self.assertNotIn('landing-endpoint-tag', html)
        self.assertLess(html.index('Адрес MCP-сервера'), html.index('class="landing-endpoint"'))
        self.assertIn('navigator.clipboard.writeText', pages.LANDING_COPY_JS)
        self.assertIn('Один адрес. Семьдесят два инструмента. Никакого шаманского бубна.', html)
        self.assertIn('Коты и собаки в списке поддерживаемых', html)
        self.assertIn('пока проходят испытательный срок.', html)
        self.assertLess(html.index('class="landing-endpoint"'), html.index('Никакого шаманского бубна'))
        self.assertLess(html.index('Никакого шаманского бубна'), html.index('class="landing-steps"'))
        self.assertLess(html.index('class="landing-steps"'), html.index('class="landing-disclaimer"'))
        self.assertIn('Скопировано. Вербуйте своего агента!', pages.LANDING_COPY_JS)
        self.assertIn('hint.textContent = originalHint', pages.LANDING_COPY_JS)
        self.assertIn('delete hint.dataset.copied', pages.LANDING_COPY_JS)

    def test_landing_escapes_untrusted_endpoint(self):
        injected = 'https://example.test/?a=<script>alert(1)</script>&x="'
        html = pages.home_page(injected)
        self.assertNotIn(injected, html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&amp;x=&quot;', html)

    def test_other_pages_do_not_load_landing_javascript(self):
        for html in (
            pages.login_page(
                action='/signin', hidden={'flow': 'flow-id'},
                heading='Вход', lead='Вход в YouGile',
            ),
            pages.company_page(action='/signin/company', hidden={},
                               companies=[('a', 'A')]),
            pages.message_page('Ошибка', 'Нет доступа'),
        ):
            self.assertNotIn('/assets/landing.js', html)

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
