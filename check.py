import asyncio
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright

START = 'https://www.rotterdam.nl/handtekening-legaliseren'
OUT = Path('debug')
OUT.mkdir(exist_ok=True)

async def dismiss_cookies(page):
    for label in ['Weiger cookies', 'Weigeren', 'Reject cookies']:
        button = page.get_by_text(label, exact=True)
        if await button.count():
            try:
                await button.first.click(timeout=3000)
                return
            except Exception:
                pass

async def notify(context, message):
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id:
        raise RuntimeError('Telegram secrets are missing')
    response = await context.request.post(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data={'chat_id': chat_id, 'text': message},
        timeout=20000,
    )
    if not response.ok:
        raise RuntimeError(f'Telegram HTTP {response.status}: {(await response.text())[:200]}')
    payload = await response.json()
    if not payload.get('ok'):
        raise RuntimeError('Telegram rejected the message')
    print('Telegram message sent successfully')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(locale='nl-NL', viewport={'width': 1366, 'height': 900})
        page = await context.new_page()
        appointment = page
        try:
            if os.getenv('TEST_TELEGRAM') == 'true':
                await notify(context, 'Test: GitHub cloud Prins Alexander monitor connected.')
                return
            await page.goto(START, wait_until='domcontentloaded', timeout=45000)
            print('Landing page:', page.url)
            await dismiss_cookies(page)
            first_link = page.get_by_role('link', name=re.compile('Afspraak maken', re.I))
            await first_link.first.click(timeout=15000)
            await page.wait_for_url(re.compile('start-handtekening-legaliseren'), timeout=20000)
            print('Start page:', page.url)
            await dismiss_cookies(page)
            second_link = page.get_by_role('link', name=re.compile('Afspraak maken', re.I))
            async with context.expect_page(timeout=20000) as popup:
                await second_link.first.click(timeout=15000)
            appointment = await popup.value
            await appointment.wait_for_load_state('domcontentloaded', timeout=30000)
            print('Appointment page:', appointment.url)
            await appointment.get_by_role('button', name='Verder').click(timeout=15000)
            print('Clicked Verder')
            await appointment.get_by_text('Prins Alexander', exact=True).first.wait_for(timeout=30000)
            card = await appointment.evaluate(r'''() => {
                const elements = [...document.querySelectorAll('body *')];
                const name = elements.find(el => el.children.length === 0 &&
                    el.textContent.trim().toLowerCase() === 'prins alexander');
                if (!name) return null;
                let node = name;
                for (let i = 0; i < 7 && node; i++, node = node.parentElement) {
                    const text = (node.innerText || '').trim();
                    if (text.length < 350 && text.toLowerCase().includes('prins alexander') &&
                        (/geen tijden beschikbaar/i.test(text) || /vanaf\s+\d/i.test(text))) return text;
                }
                return null;
            }''')
            if not card:
                raise RuntimeError('Prins Alexander card not recognized')
            print('Prins Alexander card:', card)
            if re.search('Geen tijden beschikbaar', card, re.I):
                print('RESULT: EMPTY (no available slots)')
            elif re.search(r'vanaf\s+\d', card, re.I):
                print('RESULT: POSSIBLY AVAILABLE — manually verify')
                await notify(context, 'Prins Alexander: possible appointment availability! Check Rotterdam appointment website now.\n' + START)
            else:
                raise RuntimeError('Unrecognized Prins Alexander availability status')
        except Exception as exc:
            print('RESULT: UNKNOWN:', repr(exc))
            raise
        finally:
            print('Final URL:', appointment.url)
            try:
                await appointment.screenshot(path=str(OUT / 'appointment.png'), full_page=True)
            except Exception as exc:
                print('Screenshot failed:', repr(exc))
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
