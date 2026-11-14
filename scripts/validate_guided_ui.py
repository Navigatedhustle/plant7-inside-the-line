#!/usr/bin/env python3
"""Exercise the one-button story, failure recovery, capability isolation and screen fit."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.cache/playwright'))


async def main(base, recorded_only, out):
    out.mkdir(parents=True, exist_ok=True)
    checks = {}
    errors, external = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--disable-background-networking'])
        context = await browser.new_context(viewport={'width': 1366, 'height': 768}, device_scale_factor=1)
        async def restrict(route):
            if urlparse(route.request.url).netloc != urlparse(base).netloc:
                external.append(route.request.url)
                await route.abort()
            else:
                await route.continue_()
        await context.route('**/*', restrict)
        page = await context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        await page.goto(base + ('/?walkthrough=recorded' if recorded_only else '/'), wait_until='networkidle')
        await page.wait_for_function('() => window.p7 !== undefined')
        assert await page.get_by_text('Presenter access', exact=True).count() == 0
        assert await page.locator('#next').is_enabled()
        sid = await page.evaluate('p7.sid')
        await page.locator('#next').click()
        await page.wait_for_function('() => p7.state.chapter === 1')
        assert await page.locator('#back').is_enabled()
        await page.locator('#next').click()
        await page.wait_for_function('() => p7.state.chapter === 2')
        await page.wait_for_function('() => p7.job?.status === "completed"', timeout=120000)
        assert (await page.evaluate('p7.job.mode')) == ('captured_replay' if recorded_only else 'live_local')
        rid = await page.evaluate('p7.job.run_id')
        await page.locator('#next').click()
        await page.wait_for_function('() => p7.state.chapter === 3')
        assert await page.locator('.unit-grid button').count() == 539
        await page.locator('.unit-grid button.exception').first.click()
        await page.get_by_text('Station history', exact=True).wait_for()
        await page.locator('#close-drawer').click()
        await page.locator('#prepare').click()
        await page.locator('#approver').fill('Guided acceptance reviewer')
        await page.locator('#confirm-hold').click()
        await page.get_by_text('Simulated hold applied', exact=True).wait_for()
        await page.locator('#close-drawer').click()
        assert await page.locator('.unit-grid button.hold').count() == 539
        await page.locator('#next').click()
        await page.wait_for_function('() => p7.state.chapter === 4')
        assert await page.locator('#token-value').is_visible()
        usage = await page.evaluate('p7.job.token_economics')
        assert usage['usage_complete'] and usage['prompt_tokens'] > 0 and usage['completion_tokens'] > 0
        await page.locator('#price-input').fill('0')
        await page.locator('#price-output').fill('0')
        assert await page.locator('#cloud-equivalent').inner_text() == '$0.00'
        await page.locator('#price-input').fill('2')
        await page.locator('#price-output').fill('8')
        await page.locator('#price-volume').fill('2000')
        expected = (usage['prompt_tokens'] * 2 + usage['completion_tokens'] * 8) * 2000 / 1e6
        assert await page.locator('#cloud-equivalent').inner_text() == '${:,.2f}'.format(expected)
        await page.locator('#price-volume').fill('-1')
        assert await page.locator('#cloud-equivalent').inner_text() == '—'
        await page.locator('#price-volume').fill('1000')
        checks['guided_path'] = 'Four main-button clicks: local investigation or explicit recording, source playback, exact scope, decision and token economics'
        checks['token_usage'] = {'mode': usage['basis'], 'input': usage['prompt_tokens'], 'output': usage['completion_tokens'], 'scope': usage['scope'], 'arithmetic': 'zero rates, changed volume and invalid input verified'}
        checks['impactful_details'] = 'Exception unit passport, exact cohort, named simulated hold and reviewable exports'
        for kind in ('brief', '8d', 'json'):
            response = await context.request.get(base + f'/api/stage/jobs/{rid}/export/{kind}')
            assert response.status == 200
        await page.reload(wait_until='networkidle')
        await page.wait_for_function('() => window.p7 !== undefined')
        assert await page.evaluate('p7.state.chapter') == 4
        assert await page.evaluate('p7.job.run_id') == rid
        assert await page.evaluate('Object.keys(window.p7holds).length') == 539
        checks['refresh'] = 'Chapter, run and exact simulated hold set survive refresh'
        for width, height in [(1920, 1080), (1440, 900), (1366, 768), (1280, 720)]:
            await page.set_viewport_size({'width': width, 'height': height})
            for chapter in range(5):
                await page.evaluate('(chapter) => p7.change({chapter})', chapter)
                await page.wait_for_timeout(180)
                dimensions = await page.evaluate('''() => {
                    const panel=document.querySelector('#panel'), token=document.querySelector('#token-value'), next=document.querySelector('#next');
                    return {width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,panel:panel.scrollHeight-panel.clientHeight,token:token.hidden?0:token.scrollHeight-token.clientHeight,next:next.getBoundingClientRect().bottom};
                }''')
                assert dimensions['width'] <= width and dimensions['height'] <= height, dimensions
                assert dimensions['panel'] <= 1 and dimensions['token'] <= 1 and dimensions['next'] <= height, (chapter, dimensions)
            await page.screenshot(path=str(out / f'value-{width}x{height}.png'))
            checks[f'fit_{width}x{height}'] = 'All five steps: no page, evidence-panel or value-card scrolling; main action visible'
        # Same run may complete without a session revision; wall must refresh its job status too.
        wall = await context.new_page()
        await wall.goto(base + '/wall?session=' + sid, wait_until='networkidle')
        await wall.wait_for_function('() => window.p7 !== undefined')
        assert await wall.locator('#next').is_visible() is False
        assert await wall.evaluate('p7.job.run_id') == rid
        phone = await context.new_page()
        await phone.set_viewport_size({'width': 390, 'height': 844})
        requests = []
        phone.on('request', lambda r: requests.append(r.url))
        await phone.goto(base + '/m?session=' + sid, wait_until='networkidle')
        await phone.wait_for_function('() => window.p7 !== undefined')
        assert await phone.locator('canvas').count() == 0
        assert not any('/scene-' in x for x in requests)
        checks['following_views'] = 'Wall remains read only; mobile loads no 3D assets or stage controls'
        await wall.close()
        await phone.close()
        await page.locator('#next').click()
        await page.wait_for_function('() => p7.state.chapter === 0 && p7.job === null')
        assert await page.evaluate('Object.keys(window.p7holds).length') == 0
        # A second browser tab owns a different control capability, without a key prompt.
        other = await context.new_page()
        await other.goto(base, wait_until='networkidle')
        await other.wait_for_function('() => window.p7 !== undefined')
        assert await other.evaluate('p7.sid') != sid
        await other.close()
        if not recorded_only:
            # Endpoint failure must not fabricate a successful run or trap the audience.
            await page.route('**/api/stage/sessions/*/jobs', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"Injected temporary outage"}'))
            await page.locator('#next').click()
            assert await page.evaluate('p7.state.chapter') == 0
            await page.wait_for_function('() => !document.querySelector("#next").disabled')
            await page.unroute('**/api/stage/sessions/*/jobs')
            # Simulate a saved failed run to exercise the explicit replay recovery button.
            await page.evaluate('''() => {p7.change({chapter:2});}''')
            await page.locator('#next').click()
            await page.wait_for_function('() => p7.job !== null')
            await page.locator('#back').click()
            await page.keyboard.press('ArrowRight')
            await page.wait_for_function('() => p7.state.chapter === 2')
            await page.wait_for_function('() => ["completed","failed"].includes(p7.job?.status)', timeout=120000)
            checks['submission_failure'] = '503 keeps the first step usable; retry runs the real workflow'
            failed = await page.evaluate('JSON.parse(JSON.stringify(p7.job))')
            failed['status'] = 'failed'
            failed.pop('answer', None)
            failed['events'].append({'type':'error','label':'Injected lost model connection'})
            await page.route('**/api/stage/jobs/' + failed['run_id'], lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(failed)))
            await page.reload(wait_until='networkidle')
            await page.wait_for_function('() => window.p7 !== undefined')
            await page.locator('#replay').wait_for(state='visible')
            await page.locator('#replay').click()
            await page.wait_for_function('() => p7.job?.mode === "captured_replay" && p7.job?.status === "completed"')
            await page.locator('#mode').filter(has_text='RECORDED').wait_for()
            checks['failed_run_recovery'] = 'Failed saved run exposes explicit recorded recovery, with no accepted live answer'

        # Explicit recording mode is available without mistaking it for live inference.
        recorded = await context.new_page()
        await recorded.goto(base + '/?walkthrough=recorded', wait_until='networkidle')
        await recorded.wait_for_function('() => window.p7 !== undefined')
        await recorded.locator('#next').click()
        await recorded.wait_for_function('() => p7.job?.mode === "captured_replay"')
        assert 'RECORDED' in await recorded.locator('#mode').inner_text()
        checks['recorded_mode'] = 'Recording chosen before the first step; persistent label and historical token basis'
        await recorded.close()
        assert not errors, errors
        assert not external, external
        await context.close()
        await browser.close()
        fallback = await p.chromium.launch(headless=True, args=['--disable-webgl', '--disable-background-networking'])
        fallback_page = await fallback.new_page(viewport={'width': 1366, 'height': 768})
        await fallback_page.goto(base + '/?walkthrough=recorded', wait_until='networkidle')
        await fallback_page.wait_for_function('() => window.p7 !== undefined')
        assert await fallback_page.locator('#fallback').is_visible()
        await fallback_page.locator('#next').click()
        await fallback_page.locator('[data-bolt="B2"]').click()
        await fallback_page.get_by_text('B2 · its actual source record', exact=True).wait_for()
        await fallback.close()
        checks['webgl_fallback'] = '2D source inspection works without WebGL'
    result = {'checks': checks, 'page_errors': errors, 'external_requests': external, 'base': base}
    (out / 'guided-audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8097')
    parser.add_argument('--recorded-only', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/captures/guided')
    args = parser.parse_args()
    asyncio.run(main(args.base.rstrip('/'), args.recorded_only, args.output))
