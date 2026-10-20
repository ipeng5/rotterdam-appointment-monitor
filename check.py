import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

START = 'https://www.rotterdam.nl/handtekening-legaliseren'
OUT = Path('debug')
OUT.mkdir(exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(locale='nl-NL', viewport={'width': 1366, 'height': 900})
        page = await context.new_page()
        try:
            await page.goto(START, wait_until='domcontentloaded', timeout=45000)
            print('Landing page:', page.url)
            # Cookie consent may obstruct clicks; prefer reject.
            for label in ['Weiger cookies', 'Weigeren', 'Reject cookies']:
                button = page.get_by_text(label, exact=True)
                if await button.count():
                    try:
                        await button.first.click(timeout=3000)
                        break
                    except Exception:
                        pass
            link = page.get_by_role('link', name=re.compile('Afspraak maken', re.I))
            if not await link.count():
                link = page.get_by_text('Afspraak maken', exact=True)
            if not await link.count():
                raise RuntimeError('Could not find Afspraak maken link')
            async with context.expect_page(timeout=10000) as opened:
                # Some sites open a new tab. If same-tab, fallback below.
                await link.first.click(timeout=15000)
            appointment = await opened.value
        except Exception as exc:
            # If click navigated same tab, it may have succeeded even if expect_page timed out.
            if 'appointment' not in locals() and 'concern.ir.rotterdam.nl' in page.url:
                appointment = page
            else:
                print('Navigation issue:', repr(exc))
                appointment = page
        try:
            await appointment.wait_for_load_state('domcontentloaded', timeout=25000)
            await appointment.get_by_text('Prins Alexander', exact=True).first.wait_for(timeout=25000)
            cards = await appointment.evaluate(r'''() => {
              const matches = [...document.querySelectorAll('body *')].filter(el =>
                el.textContent && el.textContent.trim().toLowerCase() === 'prins alexander');
              for (const el of matches) {
                let node = el;
                for (let i = 0; i < 5 && node; i++, node = node.parentElement) {
                  const t = (node.innerText || '').trim();
                  if (t.length < 250 && t.toLowerCase().includes('prins alexander') &&
                      (/geen tijden beschikbaar/i.test(t) || /vanaf\s+\d/i.test(t))) return t;
                }
              }
              return null;
            }''')
            if not cards:
                raise RuntimeError('Prins Alexander card not recognized')
            print('Prins Alexander card:', cards)
            if re.search('Geen tijden beschikbaar', cards, re.I):
                print('RESULT: EMPTY (no available slots)')
            elif re.search(r'vanaf\s+\d', cards, re.I):
                print('RESULT: POSSIBLY AVAILABLE — manually verify')
            else:
                print('RESULT: UNKNOWN')
        except Exception as exc:
            print('RESULT: UNKNOWN:', repr(exc))
            raise
        finally:
            print('Final URL:', appointment.url)
            await appointment.screenshot(path=str(OUT / 'appointment.png'), full_page=True)
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
