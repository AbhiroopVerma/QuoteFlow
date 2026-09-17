// Run against the local server; only cases created by this test are deleted.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');

(async () => {
  await fs.mkdir('work/browser', {recursive:true});
  const browser = await chromium.launch({headless:true, ...(process.env.BROWSER_CHANNEL ? {channel:process.env.BROWSER_CHANNEL} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[], created=[];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto('http://127.0.0.1:8765');
    await page.getByRole('heading',{name:'Enquiries',exact:true}).waitFor();
    assert(await page.locator('svg.lucide').count() > 5, 'Lucide icons rendered');
    await page.screenshot({path:'work/browser/inbox-desktop.png',fullPage:true});
    await page.getByRole('button',{name:/Standard order/}).click();
    await page.getByRole('checkbox').check();
    const createdResponse = page.waitForResponse(r=>r.url().endsWith('/api/cases')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Create enquiry',exact:true}).click();
    const first = await (await createdResponse).json(); created.push(first.id);
    await page.getByRole('button',{name:'Confirm & calculate'}).click();
    await page.getByText('1,866.63',{exact:true}).waitFor();
    await page.screenshot({path:'work/browser/pricing-desktop.png',fullPage:true});
    await page.getByRole('button',{name:'Preview quote',exact:true}).click();
    await page.getByRole('button',{name:'Mark reviewed',exact:true}).click();
    await page.getByRole('button',{name:'Reviewed',exact:true}).waitFor();
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button',{name:'Download PDF',exact:true}).click();
    await (await downloadPromise).saveAs('work/browser/quote.pdf');
    await page.screenshot({path:'work/browser/preview-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'work/browser/preview-mobile.png',fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), 'No horizontal page overflow');
    await page.getByRole('button',{name:'All enquiries',exact:true}).click();
    await page.getByRole('button',{name:/Product clarification/}).click();
    await page.getByRole('checkbox').check();
    const secondResponse=page.waitForResponse(r=>r.url().endsWith('/api/cases')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Create enquiry',exact:true}).click();
    created.push((await (await secondResponse).json()).id);
    await page.getByText('Do you need ABS or metal boxes?',{exact:true}).waitFor();
    await page.getByLabel('Product line 1',{exact:true}).selectOption('BX-IP65-2015-M');
    await page.getByRole('button',{name:'Confirm & calculate'}).click();
    await page.getByText('662.72',{exact:true}).waitFor();
    await page.screenshot({path:'work/browser/pricing-mobile.png',fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), 'Mobile pricing fits');
    await page.getByRole('button',{name:'All enquiries',exact:true}).click();
    await page.getByRole('button',{name:/Commercial exception/}).click();
    await page.getByRole('checkbox').check();
    const thirdResponse=page.waitForResponse(r=>r.url().endsWith('/api/cases')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Create enquiry',exact:true}).click();
    created.push((await (await thirdResponse).json()).id);
    await page.getByRole('button',{name:'Confirm & calculate'}).click();
    await page.getByRole('checkbox').check();
    await page.getByRole('button',{name:'Record delivery decision'}).click();
    await page.getByRole('button',{name:'View approvals'}).click();
    await page.getByText('Finance Approver',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Preview',exact:true}).last().click();
    assert(await page.getByRole('button',{name:'Mark reviewed'}).isDisabled(), 'Commercial approval stays blocked');
    assert.deepEqual(errors, []);
    console.log('Browser passed: happy path, PDF, clarification, stock consent, approval hold, mobile overflow, no JS errors.');
  } finally {
    await page.evaluate(async ids=>{for(const id of ids){const r=await fetch(`/api/cases/${id}`);const c=await r.json();await fetch(`/api/cases/${id}`,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:c.revision})});}},created);
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
