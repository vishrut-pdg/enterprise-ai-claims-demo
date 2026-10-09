import { test, expect } from '@playwright/test'

test('AI analytics is navigable and reports durable usage without changing claims',async({page})=>{
 await page.goto('/')
 if(await page.getByRole('link',{name:'Decision history',exact:true}).count()){
  await expect.poll(async()=>{const claims=await (await page.request.get('/api/claims')).json();return claims.every((c:{status:string})=>['accepted','rejected'].includes(c.status))},{timeout:120000}).toBe(true)
 }
 const before=await (await page.request.get('/api/claims')).json()
 const chat=await page.request.post('/api/chat',{data:{message:'What expense claims are in this queue?',history:[]}})
 expect(chat.ok()).toBe(true)
 await page.getByRole('link',{name:'AI usage & performance',exact:true}).click()
 await expect(page.getByRole('heading',{name:'AI usage & performance',exact:true})).toBeVisible()
 await expect(page.getByRole('heading',{name:'Recent model requests'})).toBeVisible()
 const response=await page.request.get('/api/analytics/ai?days=0')
 expect(response.ok()).toBe(true)
 const metrics=await response.json()
 expect(metrics.summary.requests).toBeGreaterThan(0)
 expect(metrics.requests.some((r:{operation:string,status:string})=>r.operation==='chat' && r.status==='succeeded')).toBe(true)
 expect(metrics.summary.priced_requests).toBeGreaterThan(0)
 await page.getByLabel('Period').selectOption('0')
 await page.getByRole('button',{name:'Claim runs',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Recent claim runs'})).toBeVisible()
 await page.screenshot({path:'test-results/ai-analytics.png',fullPage:true})
 const after=await (await page.request.get('/api/claims')).json()
 expect(after).toEqual(before)
})
