// Optional browser smoke test. Pass an installed playwright-core path as argument.
const {chromium} = require(process.argv[2] || 'playwright-core');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
    await page.waitForSelector('canvas');
    assert.equal(await page.evaluate(() => window.PALLET_DATA.boxes.length),20);
    assert.equal(await page.locator('canvas').count(),1);
    for (const box of await page.evaluate(() => window.PALLET_DATA.boxes)) {
      await page.locator(`[data-box="${box.box_id}"]`).click();
      assert.match(await page.locator('#box-location').innerText(),new RegExp(box.box_id));
      assert.equal(await page.locator('#observed-mean').innerText(),box.hour_24_mean.toFixed(2));
    }
    await page.locator('[data-box="L3B12"]').click();
    assert.equal(await page.locator('#first-crossing').innerText(),'Not reached by hour 24');
    await page.locator('[data-hour="6"]').click();
    const expected = await page.evaluate(() => window.PALLET_DATA.boxes.find(b=>b.box_id==='L3B12').observed.find(r=>r.hour===6).mean_value.toFixed(2));
    assert.equal(await page.locator('#observed-mean').innerText(),expected);
    await page.locator('[data-layer="4"]').click();
    assert.match(await page.locator('#box-location').innerText(),/Layer 4/);
    await page.locator('[data-layer="all"]').click();
    await page.locator('#explode-slider').fill('12');
    assert.equal(await page.locator('#explode-value').innerText(),'100%');
    await page.locator('#explode-slider').fill('0');
    await page.locator('[data-hour="24"]').click();
    const canvas = page.locator('canvas');
    await canvas.scrollIntoViewIfNeeded();
    const bounds = await canvas.boundingBox();
    let picked = false;
    for (let y=80;y<bounds.height-80 && !picked;y+=35) {
      for (let x=80;x<bounds.width-80 && !picked;x+=35) {
        await page.mouse.move(bounds.x+x,bounds.y+y);
        if (await page.locator('#hover-tip').isVisible()) {
          const id=(await page.locator('#hover-tip').innerText()).split(' ')[0];
          await page.mouse.click(bounds.x+x,bounds.y+y);
          assert.ok((await page.locator('#box-location').innerText()).includes(id));
          picked=true;
        }
      }
    }
    assert.ok(picked,'A rendered box face can be selected');
    const before=await canvas.screenshot();
    await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
    await page.mouse.down();
    await page.mouse.move(bounds.x+bounds.width/2+180,bounds.y+bounds.height/2+25,{steps:10});
    await page.mouse.up();
    await page.waitForTimeout(100);
    assert.ok(!before.equals(await canvas.screenshot()),'Dragging changes the 3D view');
    await page.locator('#reset-view').click();
    await page.locator('#play-time').click();
    await page.waitForTimeout(1550);
    assert.equal(await page.locator('#time-caption').innerText(),'Hour 6 of 24');
    await page.locator('#play-time').click();
    await page.locator('[data-hour="24"]').click();
    await page.locator('[data-box="L1B1"]').click();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false);
    await page.screenshot({path:path.join(__dirname,'preview.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.waitForTimeout(200);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false,'Mobile horizontal overflow');
    await page.setViewportSize({width:1440,height:1000});
    await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href+'?box=L2B7&hour=6');
    assert.match(await page.locator('#box-location').innerText(),/L2B7/);
    assert.equal(await page.locator('#time-caption').innerText(),'Hour 6 of 24');
    assert.match(await page.locator('#alignment-note').innerText(),/2 outer vertical sides/);
    await page.locator('#box-data-link').click();
    await page.waitForFunction(()=>document.querySelector('#box-picker')?.options.length===20);
    assert.equal(await page.locator('#box-picker').inputValue(),'L2B7');
    assert.equal(await page.locator('#hour-picker').inputValue(),'6');
    assert.equal(await page.locator('#observed-table tbody tr').count(),13);
    assert.equal(await page.locator('#simulation-table tbody tr').count(),5);
    assert.equal(await page.locator('#trial-table tbody tr').count(),5);
    assert.equal(await page.locator('#sample-table tbody tr').count(),500);
    assert.equal(await page.locator('#alignment-table tr.flagged').count(),2);
    assert.equal(await page.locator('[data-map-box]').count(),20);
    await page.locator('#box-picker').selectOption('L2B9');
    assert.match(await page.locator('#selected-alignment').innerText(),/vertical outer sides: 1/);
    await page.locator('[data-map-box="L4B20"]').click();
    assert.equal(await page.locator('#box-picker').inputValue(),'L4B20');
    await page.locator('#hour-picker').selectOption('18');
    await page.locator('#view-box').click();
    await page.waitForFunction(()=>document.querySelector('#box-location')?.textContent.includes('L4B20'));
    assert.match(await page.locator('#box-location').innerText(),/L4B20/);
    assert.equal(await page.locator('#time-caption').innerText(),'Hour 18 of 24');
    await page.locator('#box-data-link').click();
    await page.waitForFunction(()=>document.querySelector('#box-picker')?.options.length===20);
    await page.locator('#box-picker').selectOption('L2B7');
    await page.locator('#hour-picker').selectOption('24');
    await page.screenshot({path:path.join(__dirname,'data-preview.png'),fullPage:true});
    for(const file of await page.evaluate(()=>window.PALLET_DATA.sources)) {
      assert.ok(require('node:fs').existsSync(path.join(__dirname,file.href)),`Download exists: ${file.name}`);
    }
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false,'Data page mobile overflow');
    assert.deepEqual(errors,[]);
    console.log('PASS: offline load; all 20 box reports; time data; layer filters; separation; face selection; rotation; playback; linked data page; raw rows; two discrepancy flags; layer maps; downloadable sources; desktop/mobile layout; no browser errors.');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;});
