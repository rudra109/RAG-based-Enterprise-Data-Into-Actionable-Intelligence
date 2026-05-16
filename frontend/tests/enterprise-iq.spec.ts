import { test, expect } from '@playwright/test';

test.describe('EnterpriseIQ E2E Flows', () => {
  test('RAG chat accepts uploads and streams an answer with sources', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    await page.locator('input[type="file"]').setInputFiles({
      name: 'Q1_Report.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('The Q1 retrieval latency was 37 milliseconds. The clean data process removes duplicate rows and trims whitespace.'),
    });
    await expect(page.getByText(/successfully uploaded 1 document/i)).toBeVisible({ timeout: 10000 });

    const chatInput = page.getByPlaceholder(/ask a question/i);
    await chatInput.fill('What was the Q1 retrieval latency?');
    const sendButton = page.locator('form button[type="submit"]');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();

    await expect(page.getByText(/37 milliseconds/i)).toBeVisible({ timeout: 15000 });
    await page.getByRole('button', { name: /Q1_Report\.txt/i }).first().click();
    await expect(page.locator('.fixed').getByText(/removes duplicate rows/i)).toBeVisible();
    await page.getByLabel('Close source').click();
    await page.locator('button[title="Helpful"]').last().click();
    await expect(page.locator('button[title="Helpful"]').last()).toHaveAttribute('aria-pressed', 'true');
  });

  test('RAG chat keeps mixed documents separated and answers unsupported data questions clearly', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    await page.locator('input[type="file"]').setInputFiles([
      {
        name: 'company-cleaning-guide.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from(
          'Acme Data Cleaning Guide. The Q1 retrieval latency target is 37 milliseconds. To clean customer data, remove duplicate rows, trim extra whitespace, standardize all date formats to YYYY-MM-DD, and validate required columns before loading the data. The data owner for this process is the Data Ops Team.'
        ),
      },
      {
        name: 'bot_handlers.py',
        mimeType: 'text/x-python',
        buffer: Buffer.from(
          [
            'import re',
            'from telegram import Update',
            '',
            'def normalize_username(username):',
            '    return username.lower()',
            '',
            'def is_allowed_user(update):',
            '    return True',
            '',
            'async def authorization_guard(update, context):',
            '    return None',
            '',
            'def get_file_bot_username():',
            '    return "filebot"',
            '',
            'def get_admin_ids():',
            '    return set()',
            '',
            'async def send_clean(context, chat_id, text):',
            '    return await context.bot.send_message(chat_id, text)',
          ].join('\n')
        ),
      },
    ]);

    await expect(page.getByText(/successfully uploaded 2 document/i)).toBeVisible({ timeout: 10000 });

    const ask = async (question: string) => {
      const chatInput = page.getByPlaceholder(/ask a question/i);
      await chatInput.fill(question);
      await page.locator('form button[type="submit"]').click();
    };

    await ask('What is the Q1 retrieval latency target?');
    await expect(page.getByText(/37 milliseconds/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('button', { name: /company-cleaning-guide\.txt/i })).toBeVisible();
    await expect(page.getByText(/bot_handlers\.py/i)).toHaveCount(0);

    await ask('Who owns this process?');
    await expect(page.getByText(/Data Ops Team/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/unrelated uploads are not mixed/i)).toHaveCount(2);

    await ask('what is bot_handlers.py and how many functions are there?');
    await expect(page.getByText(/6 function definitions/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/normalize_username/i)).toBeVisible();

    await ask('how many ass file are there in my database?');
    await expect(page.getByText(/cannot count records in your real database/i)).toBeVisible({ timeout: 15000 });
  });

  test('Analytics query returns SQL, insight, chart, and data table', async ({ page }) => {
    await page.goto('/analytics');
    await page.waitForLoadState('networkidle');

    const analyticsInput = page.getByPlaceholder(/type your question here/i);
    await analyticsInput.fill('Show revenue by region');
    const sendButton = page.locator('form button[type="submit"]');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();

    await expect(page.getByText(/North America is currently leading/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/SELECT region, SUM\(revenue\)/i)).toBeVisible();
    await expect(page.locator('.recharts-responsive-container')).toBeVisible();
    await expect(page.getByRole('cell', { name: 'North America' })).toBeVisible();
  });

  test('Analytics agent changes answers based on custom workspace questions', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('enterpriseiq.workspace', 'abc');
      window.localStorage.setItem('enterpriseiq.workspaces', JSON.stringify([
        { id: '1', name: 'Enterprise Workspace', type: 'Main' },
        { id: 'abc', name: 'abc', type: 'Custom' },
      ]));
      window.localStorage.setItem('enterpriseiq.workspaceData', JSON.stringify({
        abc: {
          dataPoints: 9617,
          activeQueries: 3,
          activeUsers: 8,
          anomalies: 0,
          sources: [
            { id: 'source-1', name: 'company-cleaning-guide.txt', type: 'Text', records: 90, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-2', name: 'main.py', type: 'Code', records: 103, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-3', name: 'Perfect World [Wanmei Shijie] Ep-269.ass', type: 'Subtitle', records: 2433, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-4', name: 'The Demon Hunter [Chang Yuan Tu] Ep-77.srt', type: 'Subtitle', records: 3148, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-5', name: 'bot_handlers.py', type: 'Code', records: 1778, addedAt: '2026-05-16T00:00:00.000Z' },
          ],
        },
      }));
    });

    await page.goto('/analytics');
    await page.waitForLoadState('networkidle');

    const analyticsInput = page.getByPlaceholder(/type your question here/i);
    const sendButton = page.locator('form button[type="submit"]');

    await analyticsInput.fill('Show records by connected source');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();
    await expect(page.getByText(/largest source is The Demon Hunter/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/SELECT source_name, records/i)).toBeVisible();

    await analyticsInput.fill('Predict resource usage for the next 30 days');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();
    await expect(page.getByText(/Resource usage is projected/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/SELECT forecast_day, cpu_units, storage_gb/i)).toBeVisible();

    await analyticsInput.fill('Show me total sales by region last quarter');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();
    await expect(page.getByText(/does not currently have a connected sales/i)).toBeVisible({ timeout: 10000 });
  });

  test('Pipeline controls refresh, configure, and trigger a visible run', async ({ page }) => {
    await page.goto('/pipelines');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/Pipeline Control/i)).toBeVisible();
    await page.getByRole('button', { name: 'Refresh' }).click();
    await expect(page.getByText(/Pipeline list refreshed/i)).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: 'Config' }).click();
    await expect(page.getByText(/Pipeline Configuration/i)).toBeVisible();
    await page.getByRole('button', { name: 'Save Config' }).click();
    await expect(page.getByText(/Pipeline configuration saved/i)).toBeVisible({ timeout: 10000 });

    await page.getByText(/Sales Data Sync/i).click();
    await expect(page.getByRole('button', { name: 'Close pipeline details' })).toBeVisible();
    await page.getByRole('button', { name: 'Trigger' }).click();
    await page.getByRole('button', { name: 'Trigger Now' }).click();

    await expect(page.getByText('Running')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Run completed successfully/i)).toBeVisible({ timeout: 10000 });
  });

  test('Forecasting chart renders data and horizon changes values', async ({ page }) => {
    await page.goto('/forecasting');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/Demand Forecasting/i)).toBeVisible();
    await expect(page.locator('.recharts-line-curve')).toHaveCount(2, { timeout: 10000 });
    await expect(page.getByText(/Current horizon: 30 days/i)).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: '180d' }).click();
    await expect(page.getByRole('button', { name: '180d' })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByText(/Current horizon: 180 days/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('forecast-rmse-value')).toHaveText('8.3');
  });

  test('Forecasting supports custom workspace data', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('enterpriseiq.workspace', 'abc');
      window.localStorage.setItem('enterpriseiq.workspaces', JSON.stringify([
        { id: '1', name: 'Enterprise Workspace', type: 'Main' },
        { id: 'abc', name: 'abc', type: 'Custom' },
      ]));
      window.localStorage.setItem('enterpriseiq.workspaceData', JSON.stringify({
        abc: {
          dataPoints: 9617,
          activeQueries: 3,
          activeUsers: 8,
          anomalies: 0,
          sources: [
            { id: 'source-1', name: 'company-cleaning-guide.txt', type: 'Text', records: 90, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-2', name: 'main.py', type: 'Code', records: 103, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-3', name: 'Perfect World [Wanmei Shijie] Ep-269.ass', type: 'Subtitle', records: 2433, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-4', name: 'The Demon Hunter [Chang Yuan Tu] Ep-77.srt', type: 'Subtitle', records: 3148, addedAt: '2026-05-16T00:00:00.000Z' },
            { id: 'source-5', name: 'bot_handlers.py', type: 'Code', records: 1778, addedAt: '2026-05-16T00:00:00.000Z' },
          ],
        },
      }));
    });

    await page.goto('/forecasting');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/Predictive analytics for abc/i)).toBeVisible();
    await expect(page.getByText(/abc forecast is based on 9,617 records/i)).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.recharts-line-curve')).toHaveCount(2, { timeout: 10000 });
  });

  test('Forecasting shows a clear empty state for custom workspaces without data', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('enterpriseiq.workspace', 'empty');
      window.localStorage.setItem('enterpriseiq.workspaces', JSON.stringify([
        { id: '1', name: 'Enterprise Workspace', type: 'Main' },
        { id: 'empty', name: 'empty', type: 'Custom' },
      ]));
      window.localStorage.setItem('enterpriseiq.workspaceData', JSON.stringify({
        empty: {
          dataPoints: 0,
          activeQueries: 0,
          activeUsers: 1,
          anomalies: 0,
          sources: [],
        },
      }));
    });

    await page.goto('/forecasting');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/No forecast baseline yet/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/does not have enough historical data/i)).toBeVisible();
  });

  test('Anomaly list renders and acknowledge button updates state', async ({ page }) => {
    await page.goto('/anomalies');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/CPU Usage/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/critical/i).first()).toBeVisible();

    await page.getByRole('button', { name: 'Refresh anomalies' }).click();
    await expect(page.getByText(/Anomaly data refreshed/i)).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: '6h' }).click();
    await expect(page.getByRole('button', { name: '6h' })).toHaveAttribute('aria-pressed', 'true');
    await page.getByRole('button', { name: '24h' }).click();
    await expect(page.getByRole('button', { name: '24h' })).toHaveAttribute('aria-pressed', 'true');

    const firstAcknowledge = page.getByRole('button', { name: /acknowledge/i }).first();
    await expect(page.getByRole('button', { name: /acknowledge/i })).toHaveCount(2);
    await firstAcknowledge.click();
    await expect(page.getByRole('button', { name: /acknowledge/i })).toHaveCount(1);
    await expect(page.getByText(/Anomaly acknowledged/i)).toBeVisible({ timeout: 10000 });
  });

  test('Anomaly page shows a clear empty state for a new workspace', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('enterpriseiq.workspace', 'abcqw');
      window.localStorage.setItem('enterpriseiq.workspaces', JSON.stringify([
        { id: '1', name: 'Enterprise Workspace', type: 'Main' },
        { id: 'abcqw', name: 'abcqw', type: 'Custom' },
      ]));
      window.localStorage.setItem('enterpriseiq.workspaceData', JSON.stringify({
        abcqw: {
          dataPoints: 0,
          activeQueries: 0,
          activeUsers: 1,
          anomalies: 0,
          sources: [],
        },
      }));
    });

    await page.goto('/anomalies');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/Real-time monitoring of abcqw metrics/i)).toBeVisible();
    await expect(page.getByText(/Total Anomalies/i)).toBeVisible();
    await expect(page.getByText(/All clear! No new anomalies detected/i)).toBeVisible({ timeout: 10000 });
    await page.getByRole('button', { name: '7d' }).click();
    await expect(page.getByRole('button', { name: '7d' })).toHaveAttribute('aria-pressed', 'true');
  });
});
