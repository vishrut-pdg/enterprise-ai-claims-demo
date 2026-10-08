import { test, expect } from '@playwright/test'

test('AI automatically investigates and decides all seven claims without human actions', async ({ page }) => {
  test.setTimeout(180000)
  let manualSubmissions = 0
  let humanDecisions = 0
  page.on('request', request => {
    if (request.method() === 'POST' && request.url().includes('/jobs/assess')) manualSubmissions++
    if (request.method() === 'POST' && request.url().includes('/decisions')) humanDecisions++
  })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Claim queue', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Run', exact: true })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Manager review', exact: true })).toHaveCount(0)
  // Startup + recurring scan enqueue work without any button click.
  await expect(page.getByText('All claims decided')).toBeVisible({ timeout: 120000 })
  expect(manualSubmissions).toBe(0)
  expect(humanDecisions).toBe(0)
  await page.screenshot({ path: 'test-results/autonomous-queue.png', fullPage: true })
  for (const id of ['CLM-001', 'CLM-004', 'CLM-005']) {
    const row = page.getByRole('row').filter({ has: page.getByRole('link', { name: new RegExp(id) }) })
    await expect(row).toContainText('accepted')
  }
  for (const id of ['CLM-002', 'CLM-003', 'CLM-006', 'CLM-007']) {
    const row = page.getByRole('row').filter({ has: page.getByRole('link', { name: new RegExp(id) }) })
    await expect(row).toContainText('rejected')
  }
  await page.reload()
  await expect(page.getByText('All claims decided')).toBeVisible()
  await page.getByRole('link', { name: /CLM-003 Airport taxi/ }).click()
  await expect(page.locator('.page-heading').getByText('rejected', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'AI investigation', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Final AI decision', exact: true })).toBeVisible()
  await expect(page.getByText('ai investigation completed', { exact: true })).toBeVisible()
  await expect(page.getByText('autonomous decision recorded', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Open manager review' })).toHaveCount(0)
  await page.getByRole('button', { name: 'What evidence is missing?' }).click()
  await expect(page.getByRole('log')).toContainText(/receipt/i, { timeout: 60000 })
  await page.screenshot({ path: 'test-results/ai-investigation.png', fullPage: true })
  await page.getByRole('link', { name: 'Decision history', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Decision history', exact: true })).toBeVisible()
  await expect(page.getByText('7 records')).toBeVisible()
})
