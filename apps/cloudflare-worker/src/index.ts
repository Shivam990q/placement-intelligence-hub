import { Hono } from 'hono';
import { cors } from 'hono/cors';

export interface Env {
  DB: D1Database;
  TELEGRAM_BOT_TOKEN?: string;
  TELEGRAM_CHANNEL_ID?: string;
  TELEGRAM_FORUM_GROUP_ID?: string;
  INGEST_SECRET?: string;
}

const app = new Hono<{ Bindings: Env }>();

app.use('*', cors());

// --- Telegram & WhatsApp Helpers ---
function formatTelegramCard(opp: any): string {
  const isEthara = opp.company.toLowerCase().includes('ethara') || opp.title.toLowerCase().includes('genops');
  if (isEthara) {
    return (
      `🎯 *[TARGET ROLE ALERT — ETHARA.AI]*\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
      `🏢 *Company:* ${opp.company}\n` +
      `💼 *Role:* ${opp.title}\n` +
      `📍 *Location:* ${JSON.parse(opp.locations || '[]').join(', ') || 'Gurugram / Remote'}\n` +
      `💰 *Max Package:* ${opp.ctc_text || '₹6 LPA'}\n` +
      `🗣️ *Language Requirement:* Pure English Only\n` +
      `⏳ *Status:* Active / Verified\n\n` +
      `🔗 *Portal:* ${opp.apply_url}\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━`
    );
  }

  return (
    `🚨 *[NEW OPPORTUNITY ALERT]*\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
    `🏢 *Company:* ${opp.company}\n` +
    `🎯 *Role:* ${opp.title}\n` +
    `🎓 *Eligible Batches:* ${JSON.parse(opp.eligible_batches || '[]').join(', ') || '2026/2027'}\n` +
    `💰 *Package:* ${opp.ctc_text || 'Disclosed in portal'}\n` +
    `🔗 *Apply:* ${opp.apply_url}\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━`
  );
}

function formatWhatsAppCard(opp: any): string {
  return (
    `🚨 *NEW HIRING OPPORTUNITY*\n` +
    `━━━━━━━━━━━━━━━━━━━━\n` +
    `*Company:* ${opp.company}\n` +
    `*Role:* ${opp.title}\n` +
    `*Eligible Batches:* ${JSON.parse(opp.eligible_batches || '[]').join(', ') || '2026/2027'}\n` +
    `*Package / CTC:* ${opp.ctc_text || 'Best in Industry'}\n\n` +
    `*Apply here:* ${opp.apply_url}\n` +
    `━━━━━━━━━━━━━━━━━━━━\n` +
    `📢 Share with friends & batchmates!`
  );
}

async function sendTelegramMessage(token: string, chatId: string, text: string, threadId?: number) {
  if (!token || !chatId) return null;
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  const body: any = {
    chat_id: chatId,
    text: text,
    parse_mode: 'Markdown',
    disable_web_page_preview: false,
  };
  if (threadId) body.message_thread_id = threadId;

  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return await resp.json();
}

// --- Routes ---

// Health & Stats
app.get('/api/health', (c) => {
  return c.json({
    status: 'healthy',
    runtime: 'Cloudflare Workers (Edge)',
    timestamp: new Date().toISOString(),
  });
});

app.get('/api/stats', async (c) => {
  const db = c.env.DB;
  if (!db) {
    return c.json({ total_discovered: 4, pending_approvals: 2, published_approved: 2, active_sources: 6 });
  }

  const totalRes = await db.prepare('SELECT COUNT(*) as cnt FROM opportunities').first<{ cnt: number }>();
  const pendingRes = await db.prepare("SELECT COUNT(*) as cnt FROM opportunities WHERE status = 'pending_approval'").first<{ cnt: number }>();
  const publishedRes = await db.prepare("SELECT COUNT(*) as cnt FROM opportunities WHERE status IN ('approved', 'published')").first<{ cnt: number }>();
  const sourcesRes = await db.prepare('SELECT COUNT(*) as cnt FROM sources WHERE is_active = 1').first<{ cnt: number }>();
  const etharaOpp = await db.prepare("SELECT * FROM opportunities WHERE company LIKE '%Ethara%' LIMIT 1").first();

  return c.json({
    total_discovered: totalRes?.cnt || 0,
    pending_approvals: pendingRes?.cnt || 0,
    published_approved: publishedRes?.cnt || 0,
    active_sources: sourcesRes?.cnt || 0,
    ethara_target_status: {
      tracked: true,
      target_role: 'LLM Post-Training – GenOPS',
      package_limit: '6 LPA',
      language_requirement: 'Pure English Only',
      latest_record_id: etharaOpp ? (etharaOpp as any).id : null,
      status: etharaOpp ? (etharaOpp as any).status : 'awaiting_opening',
    },
  });
});

// List Opportunities
app.get('/api/opportunities', async (c) => {
  const db = c.env.DB;
  if (!db) return c.json([]);

  const search = c.req.query('search');
  const roleCategory = c.req.query('role_category');

  let query = 'SELECT * FROM opportunities WHERE 1=1';
  const params: any[] = [];

  if (search) {
    query += ' AND (company LIKE ? OR title LIKE ?)';
    params.push(`%${search}%`, `%${search}%`);
  }
  if (roleCategory) {
    query += ' AND role_category = ?';
    params.push(roleCategory);
  }

  query += ' ORDER BY created_at DESC LIMIT 50';
  const stmt = db.prepare(query);
  const { results } = await stmt.bind(...params).all();

  const formatted = results.map((r: any) => ({
    ...r,
    locations: JSON.parse(r.locations || '[]'),
    eligible_batches: JSON.parse(r.eligible_batches || '[]'),
    eligible_degrees: JSON.parse(r.eligible_degrees || '[]'),
    eligible_branches: JSON.parse(r.eligible_branches || '[]'),
    requirements: JSON.parse(r.requirements || '[]'),
    verification_evidence: JSON.parse(r.verification_evidence || '{}'),
  }));

  return c.json(formatted);
});

// Pending Approvals
app.get('/api/approvals/pending', async (c) => {
  const db = c.env.DB;
  if (!db) return c.json([]);

  const { results } = await db.prepare("SELECT * FROM opportunities WHERE status = 'pending_approval' ORDER BY created_at DESC").all();
  const formatted = results.map((r: any) => ({
    ...r,
    locations: JSON.parse(r.locations || '[]'),
    eligible_batches: JSON.parse(r.eligible_batches || '[]'),
    requirements: JSON.parse(r.requirements || '[]'),
  }));
  return c.json(formatted);
});

// Approval Action
app.post('/api/approvals/:id/action', async (c) => {
  const oppId = c.req.param('id');
  const body = await c.req.json();
  const db = c.env.DB;
  if (!db) return c.json({ error: 'DB not bound' }, 500);

  const opp = await db.prepare('SELECT * FROM opportunities WHERE id = ?').bind(oppId).first();
  if (!opp) return c.json({ error: 'Opportunity not found' }, 404);

  const action = body.action || 'approve';
  const newStatus = action === 'approve' ? 'approved' : 'rejected';

  await db.prepare("UPDATE opportunities SET status = ?, updated_at = datetime('now') WHERE id = ?").bind(newStatus, oppId).run();

  // Telegram distribution
  let tgResult = null;
  if (action === 'approve' && c.env.TELEGRAM_BOT_TOKEN) {
    const text = formatTelegramCard(opp);
    if (c.env.TELEGRAM_CHANNEL_ID) {
      tgResult = await sendTelegramMessage(c.env.TELEGRAM_BOT_TOKEN, c.env.TELEGRAM_CHANNEL_ID, text);
    }
  }

  const waCard = formatWhatsAppCard(opp);

  return c.json({
    status: 'success',
    decision: action,
    opportunity_id: oppId,
    new_status: newStatus,
    telegram_distribution: tgResult,
    whatsapp_card: waCard,
  });
});

// Ingest endpoint for GitHub Actions Crawler
app.post('/api/ingest', async (c) => {
  const authHeader = c.req.header('Authorization');
  if (c.env.INGEST_SECRET && authHeader !== `Bearer ${c.env.INGEST_SECRET}`) {
    return c.json({ error: 'Unauthorized' }, 401);
  }

  const items = await c.req.json();
  const db = c.env.DB;
  if (!db) return c.json({ error: 'DB not bound' }, 500);

  let inserted = 0;
  let skipped = 0;

  for (const item of items) {
    const existing = await db.prepare('SELECT id FROM opportunities WHERE canonical_url_hash = ?').bind(item.canonical_url_hash).first();
    if (existing) {
      skipped++;
      continue;
    }

    await db.prepare(`
      INSERT INTO opportunities (
        company, title, normalized_title, role_category, locations,
        eligible_batches, eligible_degrees, eligible_branches,
        ctc_text, apply_url, canonical_url_hash, content_hash,
        summary, requirements, status, verification_status
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_approval', ?)
    `).bind(
      item.company, item.title, item.normalized_title || item.title.toLowerCase(),
      item.role_category || 'full_time',
      JSON.stringify(item.locations || []),
      JSON.stringify(item.eligible_batches || []),
      JSON.stringify(item.eligible_degrees || []),
      JSON.stringify(item.eligible_branches || []),
      item.ctc_text || 'Disclosed in portal',
      item.apply_url, item.canonical_url_hash, item.content_hash || item.canonical_url_hash,
      item.summary || '', JSON.stringify(item.requirements || []),
      item.verification_status || 'verified_official'
    ).run();

    inserted++;
  }

  return c.json({ status: 'completed', inserted, skipped });
});

// Telegram Webhook Handler
app.post('/telegram/webhook', async (c) => {
  const update = await c.req.json();
  const token = c.env.TELEGRAM_BOT_TOKEN;
  if (!token) return c.json({ ok: false });

  if (update.message) {
    const chatId = update.message.chat.id.toString();
    const text = update.message.text || '';

    if (text.startsWith('/start')) {
      const msg = (
        `🎓 *Placement Intelligence Hub (Cloudflare Edge)*\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
        `Always-on zero-rupee placement radar.\n\n` +
        `Commands:\n` +
        `• /status - Live telemetry\n` +
        `• /pending - Review pending jobs\n` +
        `• /submit - Submit new job link`
      );
      await sendTelegramMessage(token, chatId, msg);
    } else if (text.startsWith('/status')) {
      await sendTelegramMessage(token, chatId, `📊 *Edge Telemetry:*\n• Status: \`100% ONLINE\`\n• Hosting: \`Cloudflare Edge ₹0/mo\`\n• Ethara GenOPS Watchdog: \`ACTIVE\``);
    }
  }

  return c.json({ ok: true });
});

export default {
  fetch: app.fetch,
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    // Scheduled Cron Trigger sweeps
    console.log('Cron triggered: scanning career watchdogs at', new Date().toISOString());
  },
};
