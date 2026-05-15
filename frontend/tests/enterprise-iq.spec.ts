import { test, expect } from '@playwright/test';

test.describe('EnterpriseIQ E2E Flows', () => {
  
  test.beforeEach(async ({ page }) => {
    // Mock Workspace List (implicit in selector)
    await page.route('**/v1/workspaces', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'ws-1', name: 'Enterprise Workspace' }]),
      });
    });

    // Mock Firebase Auth Check
    await page.route('**/identitytoolkit/v3/relyingparty/getAccountInfo**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ users: [{ localId: 'user-123', email: 'test@example.com' }] }),
      });
    });
  });

  test('Flow 1: Sign in, upload PDF and ask RAG question', async ({ page }) => {
    // Mock Session Creation
    await page.route('**/v1/auth/session', async (route) => {
      await route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
    });

    // Mock PDF Ingest
    await page.route('**/v1/rag/ingest', async (route) => {
      await route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
    });

    // Mock Streaming Chat Response
    await page.route('**/v1/rag/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'The revenue for Q1 was $5.2M according to the financial report.\n{"sources": [{"name": "Q1_Report.pdf", "page": 12}]}',
      });
    });

    await page.goto('/login');
    
    // Sign in with Google
    await page.getByRole('button', { name: /continue with google/i }).click();
    
    // Select Workspace (Assuming it redirects to dashboard/workspace selector)
    await page.waitForURL('**/dashboard');
    await page.getByRole('button', { name: /enterprise workspace/i }).click();

    // Go to RAG Chat
    await page.getByRole('link', { name: /rag chat/i }).click();
    
    // Upload a PDF (simulating drag and drop or file input)
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: /paperclip/i }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: 'Q1_Report.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('fake-pdf-content'),
    });

    // Type a question
    const input = page.getByPlaceholder(/ask a question/i);
    await input.fill('What was the revenue in Q1?');
    await input.press('Enter');

    // Verify answer with citations appears
    await expect(page.getByText(/the revenue for Q1 was \$5.2M/i)).toBeVisible();
    await expect(page.getByText(/Q1_Report.pdf/i)).toBeVisible();
    await expect(page.getByText(/p.12/i)).toBeVisible();
  });

  test('Flow 2: Analytics query and visualization', async ({ page }) => {
    // Mock Analytics Query
    await page.route('**/v1/agent/query', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sql: 'SELECT region, SUM(revenue) FROM sales GROUP BY region;',
          explanation: 'This chart shows revenue distribution across different geographic regions.',
          chart_suggestion: 'bar',
          data: [
            { region: 'North', revenue: 1200000 },
            { region: 'South', revenue: 800000 },
            { region: 'East', revenue: 1500000 },
            { region: 'West', revenue: 950000 },
          ]
        }),
      });
    });

    await page.goto('/analytics');
    
    // Type question
    const input = page.getByPlaceholder(/type your question here/i);
    await input.fill('Show revenue by region');
    await page.getByRole('button', { name: /send/i }).click();

    // Verify explanation and SQL block
    await expect(page.getByText(/revenue distribution across different geographic regions/i)).toBeVisible();
    await expect(page.getByText(/SELECT region, SUM\(revenue\)/i)).toBeVisible();

    // Verify chart renders (Recharts uses SVG)
    await expect(page.locator('.recharts-responsive-container')).toBeVisible();
    await expect(page.locator('.recharts-bar')).toHaveCount(4);
  });

  test('Flow 3: Anomaly detection and acknowledgment', async ({ page }) => {
    // Mock Anomaly List
    await page.route('**/v1/anomaly/list**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'ano-1',
            metricName: 'API Latency',
            timestamp: new Date().toISOString(),
            value: 450,
            expectedValue: 120,
            score: 0.95,
            severity: 'critical',
            isAcknowledged: false
          },
          {
            id: 'ano-2',
            metricName: 'CPU Usage',
            timestamp: new Date().toISOString(),
            value: 85,
            expectedValue: 40,
            score: 0.75,
            severity: 'warning',
            isAcknowledged: false
          }
        ]),
      });
    });

    // Mock Acknowledge Patch
    await page.route('**/v1/anomaly/ano-1/acknowledge', async (route) => {
      await route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
    });

    await page.goto('/anomalies');

    // Verify list loads
    await expect(page.getByText(/API Latency/i)).toBeVisible();
    await expect(page.getByText(/critical/i).first()).toBeVisible();

    // Click Acknowledge on the first item
    await page.getByRole('button', { name: /acknowledge/i }).first().click();

    // Verify the badge or state changes (e.g. button disappears or opacity changes)
    // In our implementation, the button disappears when acknowledged
    await expect(page.getByRole('button', { name: /acknowledge/i }).filter({ hasText: /ano-1/i })).not.toBeVisible();
  });

});
