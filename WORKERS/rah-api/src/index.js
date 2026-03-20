/**
 * RAH-API — Right at Home BnB Backend API
 * Cloudflare Worker with D1 + KV
 * Endpoints: dashboard, bookings, invoices, expenses, reviews, properties,
 *            settings, weather, assistant/chat, public/chat, guest/*,
 *            inquiries, paypal proxy
 */

// ═══════════════════════════════════════════════════════════════
// TUYA CLOUD API — Arpha D280W Smart Lock Integration
// ═══════════════════════════════════════════════════════════════

const TUYA_API_BASE = 'https://openapi.tuyaus.com'; // US data center

async function tuyaGetToken(env) {
  // Check KV cache first
  const cached = await env.CACHE.get('tuya_token', 'json');
  if (cached && cached.expires_at > Date.now()) return cached.access_token;

  const clientId = env.TUYA_CLIENT_ID;
  const clientSecret = env.TUYA_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    log('error', 'Tuya credentials not configured');
    return null;
  }

  const t = Date.now().toString();
  const signStr = clientId + t;
  const sign = await hmacSha256(signStr, clientSecret);

  const resp = await fetch(`${TUYA_API_BASE}/v1.0/token?grant_type=1`, {
    method: 'GET',
    headers: {
      'client_id': clientId,
      'sign': sign,
      't': t,
      'sign_method': 'HMAC-SHA256',
    },
  });

  const data = await resp.json();
  if (!data.success) {
    log('error', 'Tuya token failed', { code: data.code, msg: data.msg });
    return null;
  }

  const tokenData = {
    access_token: data.result.access_token,
    refresh_token: data.result.refresh_token,
    expires_at: Date.now() + (data.result.expire_time * 1000) - 60000, // 1 min buffer
  };
  await env.CACHE.put('tuya_token', JSON.stringify(tokenData), { expirationTtl: data.result.expire_time - 60 });
  return tokenData.access_token;
}

async function tuyaRequest(method, path, env, body = null) {
  const token = await tuyaGetToken(env);
  if (!token) return { success: false, msg: 'No Tuya token' };

  const clientId = env.TUYA_CLIENT_ID;
  const clientSecret = env.TUYA_CLIENT_SECRET;
  const t = Date.now().toString();
  const signStr = clientId + token + t;
  const sign = await hmacSha256(signStr, clientSecret);

  const url = `${TUYA_API_BASE}${path}`;
  const headers = {
    'client_id': clientId,
    'access_token': token,
    'sign': sign,
    't': t,
    'sign_method': 'HMAC-SHA256',
    'Content-Type': 'application/json',
  };

  const opts = { method, headers };
  if (body && (method === 'POST' || method === 'PUT')) {
    opts.body = JSON.stringify(body);
  }

  const resp = await fetch(url, opts);
  return resp.json();
}

async function hmacSha256(message, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(message));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase();
}

// Get encryption ticket for password operations
async function tuyaGetPasswordTicket(deviceId, env) {
  const data = await tuyaRequest('POST', `/v1.0/devices/${deviceId}/door-lock/password-ticket`, env);
  if (!data.success) {
    log('error', 'Tuya password ticket failed', { code: data.code, msg: data.msg });
    return null;
  }
  return data.result; // { ticket_id, ticket_key }
}

// Create a temporary password on the lock
async function tuyaCreateTempPassword(deviceId, env, { name, code, effectiveTime, expiryTime }) {
  const ticket = await tuyaGetPasswordTicket(deviceId, env);
  if (!ticket) return { success: false, msg: 'Failed to get password ticket' };

  // Encrypt the password using AES-128-ECB with ticket_key
  const encryptedPassword = await aes128EcbEncrypt(code, ticket.ticket_key);

  const body = {
    name: name || 'Guest Code',
    password: encryptedPassword,
    effective_time: Math.floor(new Date(effectiveTime).getTime() / 1000),
    invalid_time: expiryTime ? Math.floor(new Date(expiryTime).getTime() / 1000) : 0,
    password_type: 'ticket',
    ticket_id: ticket.ticket_id,
    type: 0, // 0 = time-range, 1 = one-time
  };

  const data = await tuyaRequest('POST', `/v1.0/devices/${deviceId}/door-lock/temp-password`, env, body);
  if (!data.success) {
    log('error', 'Tuya create password failed', { code: data.code, msg: data.msg });
  }
  return data;
}

// Delete a temporary password
async function tuyaDeletePassword(deviceId, passwordId, env) {
  return tuyaRequest('DELETE', `/v1.0/devices/${deviceId}/door-lock/temp-passwords/${passwordId}`, env);
}

// Get all temporary passwords
async function tuyaListPasswords(deviceId, env) {
  return tuyaRequest('GET', `/v1.0/devices/${deviceId}/door-lock/temp-passwords?valid=true`, env);
}

// Get unlock history
async function tuyaGetOpenLogs(deviceId, env, pageNo = 1, pageSize = 20) {
  return tuyaRequest('GET', `/v1.0/devices/${deviceId}/door-lock/open-logs?page_no=${pageNo}&page_size=${pageSize}`, env);
}

// Get device info
async function tuyaGetDevice(deviceId, env) {
  return tuyaRequest('GET', `/v1.0/devices/${deviceId}`, env);
}

// Generate offline temp password (works even when lock is offline)
async function tuyaCreateOfflinePassword(deviceId, env, { name, effectiveTime, expiryTime }) {
  const body = {
    name: name || 'Offline Code',
    effective_time: Math.floor(new Date(effectiveTime).getTime() / 1000),
    invalid_time: expiryTime ? Math.floor(new Date(expiryTime).getTime() / 1000) : 0,
    type: 'multiple', // 'multiple' = reusable, 'once' = single use
  };
  return tuyaRequest('POST', `/v1.1/devices/${deviceId}/door-lock/offline-temp-password`, env, body);
}

// AES-128-ECB encryption for passwords (Tuya requirement)
async function aes128EcbEncrypt(plaintext, keyHex) {
  // Tuya ticket_key is hex — decode to raw bytes
  const keyBytes = new Uint8Array(keyHex.match(/.{1,2}/g).map(b => parseInt(b, 16)));
  // Use first 16 bytes for AES-128
  const key = await crypto.subtle.importKey('raw', keyBytes.slice(0, 16), { name: 'AES-CBC' }, false, ['encrypt']);
  // ECB = CBC with zero IV, encrypt each 16-byte block independently
  const encoder = new TextEncoder();
  let data = encoder.encode(plaintext);
  // PKCS7 padding
  const padLen = 16 - (data.length % 16);
  const padded = new Uint8Array(data.length + padLen);
  padded.set(data);
  padded.fill(padLen, data.length);
  // ECB: encrypt with zero IV (single block for short passwords)
  const iv = new Uint8Array(16); // zero IV
  const encrypted = await crypto.subtle.encrypt({ name: 'AES-CBC', iv }, key, padded);
  // Return base64
  return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
}

// ═══════════════════════════════════════════════════════════════
// TUYA INDUSTRY ASSET MANAGEMENT API
// ═══════════════════════════════════════════════════════════════

// Create an asset node in Tuya's hierarchy
async function tuyaCreateAsset(name, parentAssetId, env) {
  const body = { name };
  if (parentAssetId) body.parent_asset_id = parentAssetId;
  return tuyaRequest('POST', '/v1.0/iot-02/assets', env, body);
}

// List top-level assets (no parent)
async function tuyaListAssets(env, pageNo = 1, pageSize = 100) {
  return tuyaRequest('GET', `/v1.0/iot-02/assets?page_no=${pageNo}&page_size=${pageSize}`, env);
}

// Get a single asset by ID
async function tuyaGetAsset(assetId, env) {
  return tuyaRequest('GET', `/v1.0/iot-02/assets/${assetId}`, env);
}

// Update asset name
async function tuyaUpdateAsset(assetId, name, env) {
  return tuyaRequest('PUT', `/v1.0/iot-02/assets/${assetId}`, env, { name });
}

// Delete an asset
async function tuyaDeleteAsset(assetId, env) {
  return tuyaRequest('DELETE', `/v1.0/iot-02/assets/${assetId}`, env);
}

// Get child/sub-assets of a parent
async function tuyaGetSubAssets(assetId, env, pageNo = 1, pageSize = 100) {
  return tuyaRequest('GET', `/v1.0/iot-02/assets/${assetId}/sub-assets?page_no=${pageNo}&page_size=${pageSize}`, env);
}

// Get devices assigned to an asset
async function tuyaGetAssetDevices(assetId, env, pageNo = 1, pageSize = 100) {
  return tuyaRequest('GET', `/v1.0/iot-02/assets/${assetId}/deviceinfos?page_no=${pageNo}&page_size=${pageSize}`, env);
}

// Assign device(s) to an asset
async function tuyaAssignDeviceToAsset(assetId, deviceIds, env) {
  return tuyaRequest('POST', `/v1.0/iot-02/assets/${assetId}/devices`, env, {
    device_ids: Array.isArray(deviceIds) ? deviceIds.join(',') : deviceIds,
  });
}

// Remove device from asset
async function tuyaRemoveDeviceFromAsset(assetId, deviceId, env) {
  return tuyaRequest('DELETE', `/v1.0/iot-02/assets/${assetId}/devices/${deviceId}`, env);
}

// Authorize a user to access an asset tree node
async function tuyaAuthorizeUserToAsset(assetId, uid, env) {
  return tuyaRequest('POST', '/v1.0/iot-03/assets/actions/user-authorized', env, {
    asset_id: assetId,
    uid,
    authorized: true,
  });
}

// Generate a random numeric code
function generateCode(length = 6) {
  const digits = '0123456789';
  let code = '';
  const arr = new Uint8Array(length);
  crypto.getRandomValues(arr);
  for (const byte of arr) code += digits[byte % 10];
  // Avoid codes starting with 0 or simple patterns
  if (code[0] === '0') code = String(1 + (arr[0] % 9)) + code.slice(1);
  return code;
}

// ═══════════════════════════════════════════════════════════════
// TWILIO SMS — Text lock codes to guests
// ═══════════════════════════════════════════════════════════════

async function sendSms(to, body, env) {
  const sid = env.TWILIO_SID;
  const token = env.TWILIO_AUTH_TOKEN;
  const from = env.TWILIO_PHONE || '+14322248166';

  if (!sid || !token) {
    log('warn', 'Twilio credentials not configured, SMS not sent', { to });
    return { success: false, error: 'Twilio not configured' };
  }

  // Normalize phone — ensure +1 prefix
  let phone = to.replace(/[^\d+]/g, '');
  if (!phone.startsWith('+')) phone = phone.startsWith('1') ? `+${phone}` : `+1${phone}`;

  try {
    const resp = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${sid}/Messages.json`, {
      method: 'POST',
      headers: {
        'Authorization': 'Basic ' + btoa(`${sid}:${token}`),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ To: phone, From: from, Body: body }),
    });

    const data = await resp.json();
    if (data.sid) {
      log('info', 'SMS sent', { to: phone, message_sid: data.sid });
      return { success: true, sid: data.sid };
    }
    log('error', 'SMS failed', { to: phone, error: data.message || data.code });
    return { success: false, error: data.message || 'Unknown Twilio error' };
  } catch (e) {
    log('error', 'SMS send error', { to: phone, error: e.message });
    return { success: false, error: e.message };
  }
}

function formatGuestSms(guestName, codes, checkIn, checkOut) {
  const firstName = (guestName || 'Guest').split(' ')[0];
  const codesText = codes.map(c => `${c.lock_name}: ${c.code}`).join('\n');
  return `Hi ${firstName}! Welcome to Right at Home BnB 🏠\n\nYour door code${codes.length > 1 ? 's' : ''}:\n${codesText}\n\nCheck-in: ${checkIn} at 3:00 PM\nCheck-out: ${checkOut} at 11:00 AM\n\nThe code activates at check-in and expires at checkout. Text us if you need anything!\n\n— Right at Home BnB, Midland TX`;
}

// ═══════════════════════════════════════════════════════════════
// AUTOMATED GUEST MESSAGING — 4-MESSAGE LIFECYCLE
// Messages: pre_arrival (day before), check_in_day (morning of),
//           during_stay (mid-stay), check_out (morning of checkout)
// ═══════════════════════════════════════════════════════════════

async function getWeatherSnippet(env) {
  try {
    const cached = await env.CACHE.get('weather', 'json');
    if (cached) return `${cached.temp_f}F, ${cached.condition}`;
    const resp = await fetch('https://wttr.in/Midland,TX?format=j1', {
      headers: { 'User-Agent': 'rah-api/1.0' },
    });
    if (!resp.ok) return '';
    const data = await resp.json();
    const c = data.current_condition?.[0] || {};
    return `${c.temp_F || '--'}F, ${c.weatherDesc?.[0]?.value || ''}`;
  } catch {
    return '';
  }
}

function buildMessageBody(type, firstName, checkIn, checkOut, extras = {}) {
  switch (type) {
    case 'pre_arrival':
      return `Hi ${firstName}! We're getting Right at Home BnB ready for your arrival tomorrow (${checkIn}). Check-in is at 3:00 PM.\n\nYour door codes will be texted to you separately. If you need early check-in, just reply to this message.\n\nSafe travels!\n— Right at Home BnB`;
    case 'check_in_day': {
      const weather = extras.weather ? `\n\nMidland weather: ${extras.weather}` : '';
      return `Good morning ${firstName}! Today's the day! Welcome to Midland. Your check-in is at 3:00 PM.${weather}\n\nWiFi: ${extras.wifi || 'RightAtHome'}\nParking: Free, driveway + street\nPets: Welcome (fenced yard)\n\nText us anytime if you need anything!\n— Right at Home BnB`;
    }
    case 'during_stay':
      return `Hey ${firstName}, hope you're enjoying your stay! Just checking in to make sure everything's great.\n\nNeed restaurant recommendations, directions, or anything at all? Just text us back.\n\n— Right at Home BnB, Midland TX`;
    case 'check_out':
      return `Good morning ${firstName}! Checkout is at 11:00 AM today. Just a few reminders:\n\n- Lock the door on your way out (code will auto-expire)\n- Thermostat: please set to 72\n- Trash bins are at the curb\n\nWe'd love a review if you had a great stay! Thank you for choosing Right at Home BnB.\n\n— Right at Home BnB`;
    default:
      return '';
  }
}

async function scheduleGuestMessages(bookingId, guestId, guestName, phone, checkIn, checkOut, env) {
  if (!phone) {
    log('warn', 'No phone for guest, skipping message scheduling', { bookingId, guestName });
    return;
  }
  const firstName = (guestName || 'Guest').split(' ')[0];

  // Get wifi from settings
  let wifi = 'RightAtHome';
  try {
    const s = await env.DB.prepare("SELECT value FROM settings WHERE key = 'wifi_network'").first();
    if (s?.value) wifi = JSON.parse(s.value);
  } catch {}

  // Cancel any existing scheduled messages for this booking
  await env.DB.prepare("UPDATE scheduled_messages SET status = 'cancelled' WHERE booking_id = ? AND status = 'pending'")
    .bind(bookingId).run();

  const messages = [
    {
      type: 'pre_arrival',
      body: buildMessageBody('pre_arrival', firstName, checkIn, checkOut),
      send_at: `${checkIn}T13:00:00`, // 1 day before at 1 PM — but we need day before
    },
    {
      type: 'check_in_day',
      body: buildMessageBody('check_in_day', firstName, checkIn, checkOut, { wifi }),
      send_at: `${checkIn}T14:00:00`, // 8 AM CST = 14:00 UTC
    },
    {
      type: 'during_stay',
      body: buildMessageBody('during_stay', firstName, checkIn, checkOut),
      send_at: '', // mid-stay, calculated below
    },
    {
      type: 'check_out',
      body: buildMessageBody('check_out', firstName, checkIn, checkOut),
      send_at: `${checkOut}T14:00:00`, // 8 AM CST = 14:00 UTC on checkout day
    },
  ];

  // Calculate pre_arrival: day before check-in at 1 PM CST (19:00 UTC)
  const ciDate = new Date(checkIn + 'T00:00:00');
  const dayBefore = new Date(ciDate);
  dayBefore.setDate(dayBefore.getDate() - 1);
  messages[0].send_at = dayBefore.toISOString().split('T')[0] + 'T19:00:00';

  // Calculate during_stay: midpoint of stay at 10 AM CST (16:00 UTC)
  const coDate = new Date(checkOut + 'T00:00:00');
  const stayDays = Math.round((coDate - ciDate) / (1000 * 60 * 60 * 24));
  if (stayDays > 1) {
    const midDay = new Date(ciDate);
    midDay.setDate(midDay.getDate() + Math.floor(stayDays / 2));
    messages[2].send_at = midDay.toISOString().split('T')[0] + 'T16:00:00';
  } else {
    // 1-night stay: skip during_stay message
    messages.splice(2, 1);
  }

  // Insert all scheduled messages
  for (const msg of messages) {
    await env.DB.prepare(
      'INSERT INTO scheduled_messages (booking_id, guest_id, phone, guest_name, message_type, message_body, send_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
    ).bind(bookingId, guestId || null, phone, guestName || 'Guest', msg.type, msg.body, msg.send_at).run();
  }

  log('info', 'Scheduled guest messages', { bookingId, guestName, count: messages.length, types: messages.map(m => m.type) });
  await ingestToBrain(env, `RAH SMS: Scheduled ${messages.length} automated messages for ${guestName} (${checkIn} to ${checkOut})`, 6, ['sms', 'guest', 'automated']);
}

async function processScheduledMessages(env) {
  const now = new Date().toISOString();
  const due = await env.DB.prepare(
    "SELECT * FROM scheduled_messages WHERE status = 'pending' AND send_at <= ? AND attempts < 3 ORDER BY send_at ASC LIMIT 20"
  ).bind(now).all();

  if (due.results.length === 0) return;
  log('info', 'Processing scheduled messages', { count: due.results.length });

  for (const msg of due.results) {
    try {
      // For check_in_day messages, inject live weather
      let body = msg.message_body;
      if (msg.message_type === 'check_in_day') {
        const weather = await getWeatherSnippet(env);
        if (weather) {
          body = body.replace(/Midland weather: [^\n]*/, `Midland weather: ${weather}`);
          if (!body.includes('Midland weather:')) {
            body = body.replace('WiFi:', `Midland weather: ${weather}\n\nWiFi:`);
          }
        }
      }

      const result = await sendSms(msg.phone, body, env);

      if (result.success) {
        await env.DB.prepare(
          "UPDATE scheduled_messages SET status = 'sent', twilio_sid = ?, sent_at = datetime('now'), attempts = attempts + 1 WHERE id = ?"
        ).bind(result.sid || '', msg.id).run();
        // Log to sms_log
        await env.DB.prepare(
          "INSERT INTO sms_log (phone, message_body, direction, twilio_sid, status, scheduled_message_id) VALUES (?, ?, 'outbound', ?, 'sent', ?)"
        ).bind(msg.phone, body, result.sid || '', msg.id).run();
        log('info', 'Sent scheduled message', { id: msg.id, type: msg.message_type, guest: msg.guest_name });
        await createNotification(env, 'message', 'Guest Message Sent',
          `${msg.message_type.replace('_', ' ')} SMS sent to ${msg.guest_name}`,
          'info', '/messages', { message_id: msg.id, type: msg.message_type });
      } else {
        await env.DB.prepare(
          "UPDATE scheduled_messages SET error = ?, attempts = attempts + 1 WHERE id = ?"
        ).bind(result.error || 'Unknown error', msg.id).run();
        // Mark as failed after 3 attempts
        if (msg.attempts + 1 >= 3) {
          await env.DB.prepare("UPDATE scheduled_messages SET status = 'failed' WHERE id = ?").bind(msg.id).run();
        }
        log('warn', 'Scheduled message send failed', { id: msg.id, error: result.error, attempts: msg.attempts + 1 });
      }
    } catch (e) {
      log('error', 'Scheduled message processing error', { id: msg.id, error: e.message });
      await env.DB.prepare("UPDATE scheduled_messages SET error = ?, attempts = attempts + 1 WHERE id = ?").bind(e.message, msg.id).run();
    }
  }

  if (due.results.length > 0) {
    const sent = due.results.length;
    await ingestToBrain(env, `RAH SMS: Processed ${sent} scheduled message(s)`, 5, ['sms', 'cron', 'automated']);
  }
}

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Tenant',
    },
  });
}

function log(level, msg, ctx = {}) {
  console.log(JSON.stringify({ ts: new Date().toISOString(), level, component: 'rah-api', msg, ...ctx }));
}

function err(message, status = 400) {
  return json({ error: message }, status);
}

// ═══════════════════════════════════════════════════════════════
// FIREBASE AUTH VERIFICATION
// ═══════════════════════════════════════════════════════════════

async function verifyFirebaseToken(authHeader, env) {
  if (!authHeader || !authHeader.startsWith('Bearer ')) return null;
  const token = authHeader.slice(7);
  try {
    // Decode JWT payload (Firebase ID tokens are JWTs)
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));

    // Check expiration
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) return null;

    // Check issuer matches our Firebase project
    if (payload.iss !== `https://securetoken.google.com/${payload.aud}`) return null;

    return {
      uid: payload.user_id || payload.sub,
      email: payload.email || '',
      name: payload.name || '',
      picture: payload.picture || '',
    };
  } catch (e) {
    log('warn', 'Firebase token decode failed', { error: e.message });
    return null;
  }
}

function isOwner(user, env) {
  if (!user) return false;
  const devEmails = ['bobmcwilliams4@outlook.com', 'bobbymcwilliams@echo-op.com', 'bmcii1976@gmail.com'];
  return user.email === env.OWNER_EMAIL || devEmails.includes(user.email);
}

// ═══════════════════════════════════════════════════════════════
// SHARED BRAIN INGEST (fire-and-forget)
// ═══════════════════════════════════════════════════════════════

async function ingestToBrain(env, content, importance = 5, tags = []) {
  try {
    await env.SHARED_BRAIN.fetch('https://brain/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        instance_id: 'rah-api',
        role: 'assistant',
        content,
        importance,
        tags: ['rah', ...tags],
      }),
    });
  } catch (e) {
    log('warn', 'Brain ingest failed', { error: e.message });
  }
}

// ═══════════════════════════════════════════════════════════════
// AI CHAT (shared between /assistant/chat and /public/chat)
// ═══════════════════════════════════════════════════════════════

const GUEST_SYSTEM = `You are the friendly AI assistant for Right at Home BnB — a comfortable vacation rental in Midland, Texas, owned by Steven.

Your role: Help potential and current guests with questions about the property, booking info, amenities, local recommendations, and check-in/check-out details.

Key property info:
- Location: Midland, Texas (Permian Basin)
- Rates: Standard Room $85/night ($500/week, $1,800/month), Suite $125/night ($750/week, $2,500/month), Entire House $175/night ($1,050/week, $3,500/month)
- Cleaning fee: $75/stay, Pet fee: $50/pet/stay
- All utilities included: WiFi, electric, water, cable TV
- Fully furnished with full kitchen, washer/dryer
- Pet friendly with fenced yard
- Free parking (truck/large vehicle friendly)
- Check-in: 3:00 PM (self check-in with smart lock code — your unique code will be provided before arrival)
- Check-out: 11:00 AM (your code automatically deactivates after checkout)
- Perfect for: oilfield workers, traveling professionals, families
- Weekly and monthly discounts available

Personality: Warm, welcoming, and helpful. Like a friendly neighbor who wants to make sure you feel at home. Keep answers concise (2-3 sentences) and end with an offer to help more. For booking inquiries, encourage them to use the contact form or sign in.

Local Midland recommendations:
- Restaurants: Wall Street Bar & Grill, Garlic Press, Cork & Pig, The Petroleum Club, Rosa's Cafe, Whataburger
- Things to do: Permian Basin Petroleum Museum, I-20 Wildlife Preserve, Museum of the SW, Midland RockHounds baseball
- Shopping: Midland Park Mall, downtown shops
- Nearby: Odessa (15 min), Big Bend (~4 hrs), Carlsbad Caverns (~2 hrs)

Never discuss pricing of competitors. Always be positive about Midland and the property.`;

const OWNER_SYSTEM = `You are the AI assistant for Steven, owner of Right at Home BnB in Midland, Texas.

Your role: Help Steven manage his property — answer questions about bookings, invoicing, guests, maintenance, pricing strategy, regulations, and property management.

You have access to the dashboard data. When Steven asks about bookings, invoices, guests, expenses, or reviews, use the data you have. Be direct, professional, and helpful. Think like a property management consultant.

Key context:
- Property is in Midland, TX (Permian Basin — oil & gas hub)
- Target guests: oilfield workers, traveling nurses, families, contractors
- Rates: Standard $85/night, Suite $125/night, Entire House $175/night
- Monthly rates available for long-term stays
- Steven handles all maintenance and guest relations personally
- Uses PayPal for invoicing
- Competitive market with Airbnb/VRBO listings in the area

Be concise, actionable, and business-focused. Help Steven make more money and run a better property.`;

async function handleChat(messages, env, isPublic = false) {
  const systemPrompt = isPublic ? GUEST_SYSTEM : OWNER_SYSTEM;

  // Extract last user message from the messages array
  const userMessages = (messages || []).filter(m => m.role === 'user');
  const lastUserMsg = userMessages.length > 0 ? userMessages[userMessages.length - 1].content : '';
  if (!lastUserMsg) {
    return { choices: [{ message: { content: "Hi there! How can I help you today?" } }] };
  }

  // Build conversation context from recent messages (last 6 exchanges)
  const recentHistory = (messages || []).slice(-12).filter(m => m.role !== 'system');
  let contextBlock = '';
  if (recentHistory.length > 1) {
    const historyLines = recentHistory.slice(0, -1).map(m =>
      `${m.role === 'user' ? 'Guest' : 'Assistant'}: ${m.content}`
    ).join('\n');
    contextBlock = `\n\nRecent conversation:\n${historyLines}\n\nNow respond to the latest message:`;
  }

  // Prepend BnB system context to the message so echo-chat's LLM gets full context
  const enrichedMessage = `${systemPrompt}${contextBlock}\n\n${lastUserMsg}`;

  try {
    const resp = await env.ECHO_CHAT.fetch('https://chat/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Echo-API-Key': env.ECHO_API_KEY || '',
      },
      body: JSON.stringify({
        message: enrichedMessage,
        user_id: isPublic ? 'guest_public' : 'owner_steven',
        site_id: 'rah-midland',
        personality: 'belle',
        max_tokens: 400,
      }),
    });

    if (!resp.ok) {
      const errText = await resp.text().catch(() => '');
      log('error', 'Echo Chat failed', { status: resp.status, body: errText.slice(0, 200) });
      return { choices: [{ message: { content: "I'm having a little trouble right now. Please try again in a moment!" } }] };
    }

    const data = await resp.json();
    // echo-chat returns {response: "..."} — transform to OpenAI-style for frontend compatibility
    const reply = data.response || data.choices?.[0]?.message?.content || "I'd love to help! Please try rephrasing your question.";
    log('info', 'Chat response', { isPublic, latency_ms: data.latency_ms, personality: data.personality, provider: data.llm_provider });
    return { choices: [{ message: { content: reply } }] };
  } catch (e) {
    log('error', 'Chat error', { error: e.message, stack: e.stack });
    return { choices: [{ message: { content: "I'm temporarily offline. Feel free to use the contact form or reach out to Steven directly!" } }] };
  }
}

// ═══════════════════════════════════════════════════════════════
// SERVICE CATALOG — Predefined BnB Items
// ═══════════════════════════════════════════════════════════════

const SERVICE_CATALOG = [
  { id: 'std-night',  name: 'Standard Room — Nightly',  price: 85,    unit: 'night' },
  { id: 'std-week',   name: 'Standard Room — Weekly',   price: 500,   unit: 'week' },
  { id: 'std-month',  name: 'Standard Room — Monthly',  price: 1800,  unit: 'month' },
  { id: 'suite-night', name: 'Suite — Nightly',         price: 125,   unit: 'night' },
  { id: 'suite-week', name: 'Suite — Weekly',           price: 750,   unit: 'week' },
  { id: 'suite-month', name: 'Suite — Monthly',         price: 2500,  unit: 'month' },
  { id: 'house-night', name: 'Entire House — Nightly',  price: 175,   unit: 'night' },
  { id: 'house-week', name: 'Entire House — Weekly',    price: 1050,  unit: 'week' },
  { id: 'house-month', name: 'Entire House — Monthly',  price: 3500,  unit: 'month' },
  { id: 'clean-fee',  name: 'Cleaning Fee',             price: 75,    unit: 'stay' },
  { id: 'pet-fee',    name: 'Pet Fee',                  price: 50,    unit: 'pet' },
  { id: 'late-co',    name: 'Late Check-Out',           price: 35,    unit: 'each' },
  { id: 'early-ci',   name: 'Early Check-In',           price: 35,    unit: 'each' },
  { id: 'extra-guest', name: 'Extra Guest (over 4)',    price: 25,    unit: 'night' },
  { id: 'extra-bed',  name: 'Extra Bedding Set',        price: 20,    unit: 'each' },
  { id: 'laundry',    name: 'Laundry Service',          price: 15,    unit: 'load' },
  { id: 'grocery',    name: 'Grocery Stocking',         price: 50,    unit: 'each' },
  { id: 'transport',  name: 'Airport/Transport',        price: 40,    unit: 'trip' },
  { id: 'damage-dep', name: 'Security Deposit',         price: 200,   unit: 'stay' },
  { id: 'damage',     name: 'Damage Fee',               price: 0,     unit: 'each' },
  { id: 'discount',   name: 'Discount/Adjustment',      price: 0,     unit: 'each' },
  { id: 'custom',     name: 'Custom Item',              price: 0,     unit: 'each' },
];

// ═══════════════════════════════════════════════════════════════
// ROUTE HANDLER
// ═══════════════════════════════════════════════════════════════

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'OPTIONS') return json({ ok: true });

    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    log('info', 'Request', { method, path });

    try {
      // ─── Public (no auth) ───
      if (path === '/health') return handleHealth(env);
      if (path === '/public/chat' && method === 'POST') return handlePublicChat(request, env);
      if (path === '/inquiries' && method === 'POST') return handleInquiry(request, env, ctx);
      if (path === '/catalog') return json(SERVICE_CATALOG);

      // ─── Auth required below ───
      const user = await verifyFirebaseToken(request.headers.get('Authorization'), env);
      if (!user) return err('Unauthorized', 401);

      const owner = isOwner(user, env);

      // ─── Guest routes ───
      if (path === '/guest/bookings') return handleGuestBookings(user, env);
      if (path === '/guest/invoices') return handleGuestInvoices(user, env);
      if (path === '/guest/lock-codes') return handleGuestLockCodes(user, env);

      // ─── Worker chat (authenticated workers can ask AI for their code) ───
      if (path === '/worker/chat' && method === 'POST') return handleWorkerChat(request, user, env);

      // ─── Owner-only routes ───
      if (!owner) return err('Forbidden', 403);

      // Dashboard
      if (path === '/dashboard') return handleDashboard(env);

      // Bookings
      if (path === '/bookings' && method === 'GET') return handleListBookings(url, env);
      if (path === '/bookings' && method === 'POST') return handleCreateBooking(request, env);
      if (path.match(/^\/bookings\/\d+$/) && method === 'PUT') return handleUpdateBooking(request, path, env);
      if (path.match(/^\/bookings\/\d+$/) && method === 'DELETE') return handleDeleteBooking(path, env);

      // Guests
      if (path === '/guests' && method === 'GET') return handleListGuests(env);
      if (path === '/guests' && method === 'POST') return handleCreateGuest(request, env);
      if (path.match(/^\/guests\/\d+\/stays$/) && method === 'GET') return handleGuestStays(path, env);
      if (path.match(/^\/guests\/\d+\/communications$/) && method === 'GET') return handleGuestCommunications(path, env);

      // Invoices
      if (path === '/invoices' && method === 'GET') return handleListInvoices(url, env);
      if (path === '/invoices' && method === 'POST') return handleCreateInvoice(request, env);
      if (path.match(/^\/invoices\/\d+$/) && method === 'GET') return handleGetInvoice(path, env);
      if (path.match(/^\/invoices\/\d+$/) && method === 'PUT') return handleUpdateInvoice(request, path, env);
      if (path.match(/^\/invoices\/\d+\/send$/) && method === 'POST') return handleSendInvoice(path, env);

      // Expenses
      if (path === '/expenses' && method === 'GET') return handleListExpenses(url, env);
      if (path === '/expenses' && method === 'POST') return handleCreateExpense(request, env);
      if (path.match(/^\/expenses\/\d+$/) && method === 'DELETE') return handleDeleteExpense(path, env);

      // Reviews
      if (path === '/reviews' && method === 'GET') return handleListReviews(env);
      if (path === '/reviews' && method === 'POST') return handleCreateReview(request, env);

      // Properties
      if (path === '/properties' && method === 'GET') return handleListProperties(env);
      if (path === '/properties' && method === 'POST') return handleCreateProperty(request, env);
      if (path.match(/^\/properties\/\d+$/) && method === 'PUT') return handleUpdateProperty(request, path, env);

      // Settings
      if (path === '/settings' && method === 'GET') return handleGetSettings(env);
      if (path === '/settings' && method === 'POST') return handleSaveSettings(request, env);

      // Weather
      if (path === '/weather') return handleWeather(env);

      // Automated Messages
      if (path === '/messages' && method === 'GET') return handleListMessages(url, env);
      if (path === '/messages/stats' && method === 'GET') return handleMessageStats(env);
      if (path.match(/^\/messages\/\d+\/cancel$/) && method === 'POST') return handleCancelMessage(path, env);
      if (path === '/messages/send-now' && method === 'POST') return handleSendNow(request, env);

      // PayPal Integration
      if (path === '/paypal/config' && method === 'GET') return handlePayPalConfig(env);
      if (path === '/paypal/config' && method === 'POST') return handleSavePayPalConfig(request, env);
      if (path.match(/^\/invoices\/\d+\/paypal$/) && method === 'POST') return handleCreatePayPalInvoice(path, env);
      if (path.match(/^\/invoices\/\d+\/payment-link$/) && method === 'POST') return handlePaymentLink(path, env);
      if (path.match(/^\/invoices\/\d+\/paypal-status$/) && method === 'GET') return handlePayPalStatus(path, env);
      if (path === '/paypal/transactions' && method === 'GET') return handlePayPalTransactions(url, env);
      if (path === '/paypal/stats' && method === 'GET') return handlePayPalStats(env);
      if (path === '/payments' && method === 'GET') return handleListPayments(url, env);
      if (path.match(/^\/payments$/) && method === 'POST') return handleRecordPayment(request, env);

      // Analytics
      if (path === '/analytics' && method === 'GET') return handleAnalytics(url, env);

      // Owner Dashboard (aggregated owner view)
      if (path === '/owner/dashboard' && method === 'GET') return handleOwnerDashboard(env);

      // Admin Finance (full financial god-view)
      if (path === '/admin/finance' && method === 'GET') return handleAdminFinance(url, env);

      // Admin Costs (cost tracker with property profits)
      if (path === '/admin/costs' && method === 'GET') return handleAdminCosts(url, env);

      // Admin Reviews (enriched review management)
      if (path === '/admin/reviews' && method === 'GET') return handleAdminReviews(url, env);
      if (path.match(/^\/reviews\/\d+\/respond$/) && method === 'POST') return handleRespondToReview(request, path, env);

      // Admin CRM (enriched guest management with booking/review aggregates)
      if (path === '/admin/crm/guests' && method === 'GET') return handleCRMGuests(url, env);
      if (path.match(/^\/guests\/\d+\/notes$/) && method === 'POST') return handleUpdateGuestNotes(request, path, env);
      if (path === '/admin/crm/guests' && method === 'POST') return handleCreateCRMGuest(request, env);

      // Notifications
      if (path === '/notifications' && method === 'GET') return handleListNotifications(url, env);
      if (path === '/notifications/unread-count' && method === 'GET') return handleUnreadCount(env);
      if (path.match(/^\/notifications\/\d+\/read$/) && method === 'POST') return handleMarkRead(path, env);
      if (path === '/notifications/read-all' && method === 'POST') return handleMarkAllRead(env);
      if (path.match(/^\/notifications\/\d+$/) && method === 'DELETE') return handleDeleteNotification(path, env);

      // AI Chat (owner)
      if (path === '/assistant/chat' && method === 'POST') return handleOwnerChat(request, env);

      // ─── Smart Locks (owner-only) ───
      if (path === '/locks' && method === 'GET') return handleListLocks(env);
      if (path === '/locks/register' && method === 'POST') return handleRegisterLock(request, env);
      if (path.match(/^\/locks\/\d+$/) && method === 'GET') return handleGetLock(path, env);
      if (path.match(/^\/locks\/\d+\/guest-code$/) && method === 'POST') return handleGuestCode(request, path, env, ctx);
      if (path.match(/^\/locks\/\d+\/worker-code$/) && method === 'POST') return handleWorkerCode(request, path, env, ctx);
      if (path.match(/^\/locks\/\d+\/steven-code$/) && method === 'POST') return handleStevenCode(request, path, env, ctx);
      if (path.match(/^\/locks\/\d+\/codes$/) && method === 'GET') return handleListCodes(path, url, env);
      if (path.match(/^\/locks\/\d+\/codes\/\d+\/revoke$/) && method === 'POST') return handleRevokeCode(path, env, ctx);
      if (path.match(/^\/locks\/\d+\/activity$/) && method === 'GET') return handleLockActivity(path, url, env);
      if (path.match(/^\/locks\/\d+\/sync-activity$/) && method === 'POST') return handleSyncActivity(path, env);
      if (path.match(/^\/locks\/\d+\/unlock$/) && method === 'POST') return handleRemoteUnlock(path, env, ctx);

      // ─── Workers (cleaners, maintenance — owner-only) ───
      if (path === '/workers' && method === 'GET') return handleListWorkers(env);
      if (path === '/workers' && method === 'POST') return handleRegisterWorker(request, env, ctx);
      if (path.match(/^\/workers\/\d+$/) && method === 'DELETE') return handleDeregisterWorker(path, env, ctx);

      // ─── Asset Tree (Tuya SaaS industry pairing — owner-only) ───
      if (path === '/assets' && method === 'GET') return handleListAssets(url, env);
      if (path === '/assets' && method === 'POST') return handleCreateAsset(request, env, ctx);
      if (path === '/assets/sync' && method === 'POST') return handleSyncAssets(env, ctx);
      if (path === '/assets/initialize' && method === 'POST') return handleInitializeAssetTree(env, ctx);
      if (path.match(/^\/assets\/\d+$/) && method === 'GET') return handleGetAsset(path, env);
      if (path.match(/^\/assets\/\d+$/) && method === 'PUT') return handleUpdateAsset(request, path, env, ctx);
      if (path.match(/^\/assets\/\d+$/) && method === 'DELETE') return handleDeleteAssetNode(path, env, ctx);
      if (path.match(/^\/assets\/\d+\/children$/) && method === 'GET') return handleGetAssetChildren(path, env);
      if (path.match(/^\/assets\/\d+\/devices$/) && method === 'GET') return handleGetAssetDevices(path, env);
      if (path.match(/^\/assets\/\d+\/devices$/) && method === 'POST') return handleAssignDevice(request, path, env, ctx);
      if (path.match(/^\/assets\/\d+\/devices\/[^/]+$/) && method === 'DELETE') return handleRemoveDevice(path, env, ctx);

      return err('Not found', 404);
    } catch (e) {
      log('error', 'Unhandled error', { error: e.message, stack: e.stack, path });
      return err('Internal server error', 500);
    }
  },

  async scheduled(event, env, ctx) {
    log('info', 'Cron fired', { cron: event.cron });
    try {
      const now = new Date();
      const today = now.toISOString().split('T')[0];
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      const ds = tomorrow.toISOString().split('T')[0];

      // 1. Check upcoming check-ins (generate guest codes)
      const upcoming = await env.DB.prepare(
        'SELECT b.*, g.name, g.email, g.phone FROM bookings b LEFT JOIN guests g ON b.guest_id = g.id WHERE b.check_in = ? AND b.status != ?'
      ).bind(ds, 'cancelled').all();
      if (upcoming.results.length > 0) {
        log('info', 'Upcoming check-ins tomorrow', { count: upcoming.results.length });
        await ingestToBrain(env, `RAH: ${upcoming.results.length} guest(s) checking in tomorrow (${ds})`, 6, ['cron', 'checkin']);

        // Auto-generate guest codes for tomorrow's check-ins + TEXT them
        const locks = await env.DB.prepare('SELECT * FROM smart_locks WHERE status = ?').bind('online').all();
        for (const booking of upcoming.results) {
          // Check if code already exists for this booking
          const existing = await env.DB.prepare('SELECT id FROM access_codes WHERE booking_id = ? AND is_active = 1').bind(booking.id).first();
          if (existing) continue;

          const bookingCodes = []; // collect codes for SMS

          for (const lock of locks.results) {
            try {
              const code = generateCode(6);
              const effectiveTime = `${booking.check_in}T15:00:00`; // 3 PM check-in
              const expiryTime = `${booking.check_out}T11:30:00`; // 11:30 AM checkout + 30 min grace
              const codeName = `Guest: ${booking.name || 'Guest'} (${booking.check_in})`;

              const tuyaResult = await tuyaCreateTempPassword(lock.tuya_device_id, env, {
                name: codeName, code, effectiveTime, expiryTime,
              });

              if (tuyaResult.success) {
                await env.DB.prepare(
                  'INSERT INTO access_codes (lock_id, tuya_password_id, code, name, code_type, holder_name, holder_phone, booking_id, effective_time, expiry_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
                ).bind(lock.id, tuyaResult.result?.pwd_id || '', code, codeName, 'guest', booking.name || '', booking.phone || '', booking.id, effectiveTime, expiryTime).run();

                bookingCodes.push({ lock_name: lock.name, code });
                log('info', 'Auto-generated guest code', { booking_id: booking.id, lock: lock.name, guest: booking.name });
                await createNotification(env, 'lock', 'Guest Code Generated',
                  `Door code created for ${booking.name || 'Guest'} on ${lock.name} — check-in ${booking.check_in}`,
                  'info', '/locks', { booking_id: booking.id, lock_name: lock.name });
              }
            } catch (e) {
              log('error', 'Failed to auto-generate guest code', { booking_id: booking.id, lock: lock.name, error: e.message });
            }
          }

          // TEXT the guest their codes
          if (bookingCodes.length > 0 && booking.phone) {
            try {
              const smsBody = formatGuestSms(booking.name, bookingCodes, booking.check_in, booking.check_out);
              const smsResult = await sendSms(booking.phone, smsBody, env);
              if (smsResult.success) {
                log('info', 'Guest code SMS sent', { guest: booking.name, phone: booking.phone, codes: bookingCodes.length });
                await ingestToBrain(env, `RAH LOCKS: Texted ${bookingCodes.length} door code(s) to ${booking.name} for ${booking.check_in} check-in`, 7, ['locks', 'sms', 'guest']);
              }
            } catch (e) {
              log('error', 'Failed to text guest codes', { guest: booking.name, error: e.message });
            }
          }
        }
      }

      // 2. Revoke expired guest codes (checkout was today or earlier)
      const expired = await env.DB.prepare(
        "SELECT ac.*, sl.tuya_device_id FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.code_type = 'guest' AND ac.is_active = 1 AND ac.expiry_time <= ?"
      ).bind(now.toISOString()).all();
      for (const code of expired.results) {
        try {
          if (code.tuya_password_id) {
            await tuyaDeletePassword(code.tuya_device_id, code.tuya_password_id, env);
          }
          await env.DB.prepare("UPDATE access_codes SET is_active = 0, revoked_at = datetime('now'), revoke_reason = 'auto_expired' WHERE id = ?").bind(code.id).run();
          log('info', 'Auto-revoked expired guest code', { code_id: code.id, guest: code.holder_name });
        } catch (e) {
          log('error', 'Failed to revoke expired code', { code_id: code.id, error: e.message });
        }
      }
      if (expired.results.length > 0) {
        await ingestToBrain(env, `RAH LOCKS: Auto-revoked ${expired.results.length} expired guest code(s)`, 6, ['locks', 'cron']);
      }

      // 3. Process scheduled guest messages (4-message lifecycle)
      await processScheduledMessages(env);

      // 4. Sync lock activity from Tuya every cron run
      const allLocks = await env.DB.prepare('SELECT * FROM smart_locks').all();
      for (const lock of allLocks.results) {
        try {
          const logs = await tuyaGetOpenLogs(lock.tuya_device_id, env, 1, 20);
          if (logs.success && logs.result?.records) {
            for (const record of logs.result.records) {
              const existing = await env.DB.prepare('SELECT id FROM lock_activity WHERE tuya_record_id = ?').bind(String(record.id || record.record_id || '')).first();
              if (existing) continue;
              await env.DB.prepare(
                'INSERT INTO lock_activity (lock_id, event_type, unlock_method, user_name, tuya_record_id, details, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
              ).bind(
                lock.id,
                record.status === 'unlock' ? 'unlock' : (record.status || 'unknown'),
                record.unlock_name || record.dp_code || '',
                record.nick_name || record.user_name || '',
                String(record.id || record.record_id || ''),
                JSON.stringify(record),
                new Date((record.update_time || record.create_time || Date.now()) * 1000).toISOString()
              ).run();
            }
          }
          // Update lock status
          const deviceInfo = await tuyaGetDevice(lock.tuya_device_id, env);
          if (deviceInfo.success && deviceInfo.result) {
            await env.DB.prepare("UPDATE smart_locks SET status = ?, last_seen = datetime('now') WHERE id = ?")
              .bind(deviceInfo.result.online ? 'online' : 'offline', lock.id).run();
          }
        } catch (e) {
          log('warn', 'Lock sync failed', { lock: lock.name, error: e.message });
        }
      }
    } catch (e) {
      log('error', 'Cron error', { error: e.message });
    }
  },
};

// ═══════════════════════════════════════════════════════════════
// HEALTH
// ═══════════════════════════════════════════════════════════════

async function handleHealth(env) {
  try {
    const counts = await env.DB.prepare(`
      SELECT
        (SELECT COUNT(*) FROM bookings) as bookings,
        (SELECT COUNT(*) FROM guests) as guests,
        (SELECT COUNT(*) FROM invoices) as invoices,
        (SELECT COUNT(*) FROM expenses) as expenses,
        (SELECT COUNT(*) FROM reviews) as reviews,
        (SELECT COUNT(*) FROM properties) as properties
    `).first();
    return json({
      status: 'ok',
      version: '1.3.0',
      service: 'rah-api',
      property: 'Right at Home BnB',
      timestamp: new Date().toISOString(),
      features: ['bookings', 'invoices', 'smart-locks', 'tuya-integration', 'twilio-sms', 'automated-guest-messaging', 'weather', 'ai-chat', 'paypal-integration', 'payment-links', '3pct-surcharge', 'notifications', 'analytics'],
      counts,
    });
  } catch (e) {
    return json({ status: 'ok', version: '1.0.0', service: 'rah-api', db: 'initializing' });
  }
}

// ═══════════════════════════════════════════════════════════════
// DASHBOARD (aggregated stats)
// ═══════════════════════════════════════════════════════════════

async function handleDashboard(env) {
  const now = new Date();
  const monthStart = now.toISOString().slice(0, 7) + '-01';
  const today = now.toISOString().split('T')[0];

  const [stats, recentBookings, recentInvoices, upcoming] = await Promise.all([
    env.DB.prepare(`
      SELECT
        (SELECT COUNT(*) FROM bookings WHERE status = 'confirmed') as active_bookings,
        (SELECT COUNT(*) FROM bookings WHERE status = 'checked-in') as current_guests,
        (SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status = 'paid' AND issue_date >= ?) as month_revenue,
        (SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status IN ('sent','overdue')) as outstanding,
        (SELECT COUNT(*) FROM guests) as total_guests,
        (SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date >= ?) as month_expenses,
        (SELECT AVG(rating) FROM reviews) as avg_rating,
        (SELECT COUNT(*) FROM reviews) as review_count
    `).bind(monthStart, monthStart).first(),
    env.DB.prepare('SELECT b.*, g.name as guest_name FROM bookings b LEFT JOIN guests g ON b.guest_id = g.id ORDER BY b.created_at DESC LIMIT 5').all(),
    env.DB.prepare('SELECT * FROM invoices ORDER BY created_at DESC LIMIT 5').all(),
    env.DB.prepare("SELECT b.*, g.name as guest_name FROM bookings b LEFT JOIN guests g ON b.guest_id = g.id WHERE b.check_in >= ? AND b.status != 'cancelled' ORDER BY b.check_in LIMIT 5").bind(today).all(),
  ]);

  return json({
    stats: {
      active_bookings: stats.active_bookings || 0,
      current_guests: stats.current_guests || 0,
      month_revenue: stats.month_revenue || 0,
      outstanding: stats.outstanding || 0,
      total_guests: stats.total_guests || 0,
      month_expenses: stats.month_expenses || 0,
      avg_rating: stats.avg_rating ? parseFloat(stats.avg_rating).toFixed(1) : '5.0',
      review_count: stats.review_count || 0,
      occupancy_rate: 0, // calculated client-side from bookings
    },
    recent_bookings: recentBookings.results,
    recent_invoices: recentInvoices.results,
    upcoming_checkins: upcoming.results,
  });
}

// ═══════════════════════════════════════════════════════════════
// BOOKINGS
// ═══════════════════════════════════════════════════════════════

async function handleListBookings(url, env) {
  const status = url.searchParams.get('status');
  const limit = parseInt(url.searchParams.get('limit') || '50');
  let query = 'SELECT b.*, g.name as guest_name, g.email as guest_email, g.phone as guest_phone FROM bookings b LEFT JOIN guests g ON b.guest_id = g.id';
  const params = [];
  if (status) { query += ' WHERE b.status = ?'; params.push(status); }
  query += ' ORDER BY b.check_in DESC LIMIT ?';
  params.push(limit);
  const result = await env.DB.prepare(query).bind(...params).all();
  return json(result.results);
}

async function handleCreateBooking(request, env) {
  const body = await request.json();
  const { guest_id, room_name, check_in, check_out, status, total, notes } = body;
  if (!guest_id || !check_in || !check_out) return err('guest_id, check_in, check_out required');

  const result = await env.DB.prepare(
    'INSERT INTO bookings (guest_id, room_name, check_in, check_out, status, total, notes) VALUES (?, ?, ?, ?, ?, ?, ?)'
  ).bind(guest_id, room_name || 'Standard Room', check_in, check_out, status || 'confirmed', total || 0, notes || '').run();

  const bookingId = result.meta.last_row_id;
  log('info', 'Booking created', { bookingId, guest_id, check_in, check_out });

  // Auto-schedule the 4-message guest lifecycle SMS
  if (status !== 'cancelled') {
    try {
      const guest = await env.DB.prepare('SELECT name, phone FROM guests WHERE id = ?').bind(guest_id).first();
      if (guest?.phone) {
        await scheduleGuestMessages(bookingId, guest_id, guest.name, guest.phone, check_in, check_out, env);
      }
    } catch (e) {
      log('warn', 'Failed to schedule guest messages', { bookingId, error: e.message });
    }
  }

  // Auto-create notification
  await createNotification(env, 'booking', 'New Booking',
    `${room_name || 'Standard Room'} booked for ${check_in} — ${check_out}`,
    'success', '/bookings', { booking_id: bookingId, guest_id });

  return json({ id: bookingId, success: true }, 201);
}

async function handleUpdateBooking(request, path, env) {
  const id = path.split('/').pop();
  const body = await request.json();
  const fields = [];
  const values = [];
  for (const [k, v] of Object.entries(body)) {
    if (['room_name', 'check_in', 'check_out', 'status', 'total', 'notes'].includes(k)) {
      fields.push(`${k} = ?`);
      values.push(v);
    }
  }
  if (fields.length === 0) return err('No valid fields to update');
  values.push(id);
  await env.DB.prepare(`UPDATE bookings SET ${fields.join(', ')} WHERE id = ?`).bind(...values).run();
  return json({ success: true });
}

async function handleDeleteBooking(path, env) {
  const id = path.split('/').pop();
  await env.DB.prepare('DELETE FROM bookings WHERE id = ?').bind(id).run();
  return json({ success: true });
}

// ═══════════════════════════════════════════════════════════════
// GUESTS
// ═══════════════════════════════════════════════════════════════

async function handleListGuests(env) {
  const result = await env.DB.prepare('SELECT * FROM guests ORDER BY created_at DESC').all();
  return json(result.results);
}

async function handleCreateGuest(request, env) {
  const body = await request.json();
  const { firebase_uid, name, email, phone, is_owner } = body;

  // Upsert: if guest with this email exists, update; otherwise insert
  const existing = await env.DB.prepare('SELECT id FROM guests WHERE email = ?').bind(email).first();
  if (existing) {
    await env.DB.prepare('UPDATE guests SET name = ?, phone = ?, firebase_uid = ? WHERE id = ?')
      .bind(name || '', phone || '', firebase_uid || '', existing.id).run();
    return json({ id: existing.id, updated: true });
  }

  const result = await env.DB.prepare(
    'INSERT INTO guests (firebase_uid, name, email, phone, is_owner) VALUES (?, ?, ?, ?, ?)'
  ).bind(firebase_uid || '', name || '', email || '', phone || '', is_owner || 0).run();

  return json({ id: result.meta.last_row_id, success: true }, 201);
}

async function handleGuestStays(path, env) {
  const guestId = path.split('/')[2];
  const stays = await env.DB.prepare(`
    SELECT b.id, b.room_name, b.check_in, b.check_out, b.total, b.status,
           p.id as property_id, p.name as property_name
    FROM bookings b
    LEFT JOIN properties p ON p.name = b.room_name
    WHERE b.guest_id = ? AND b.status != 'cancelled'
    ORDER BY b.check_in DESC
    LIMIT 50
  `).bind(guestId).all();

  // Get reviews for this guest to match ratings to stays
  const guest = await env.DB.prepare('SELECT name FROM guests WHERE id = ?').bind(guestId).first();
  let reviewsByDate = {};
  if (guest) {
    const reviews = await env.DB.prepare(
      'SELECT rating, text, created_at FROM reviews WHERE guest_name = ? ORDER BY created_at DESC'
    ).bind(guest.name).all();
    for (const r of reviews.results) {
      const key = r.created_at ? r.created_at.split('T')[0] : '';
      reviewsByDate[key] = r;
    }
  }

  const result = stays.results.map(s => {
    // Try to match a review by proximity to check_out date
    let rating = undefined;
    let review = undefined;
    for (const [date, r] of Object.entries(reviewsByDate)) {
      if (date >= s.check_out) {
        rating = r.rating;
        review = r.text || undefined;
        delete reviewsByDate[date]; // consume so each review maps to one stay
        break;
      }
    }
    return {
      id: String(s.id),
      propertyId: s.property_id ? `prop-${s.property_id}` : s.room_name,
      propertyName: s.property_name || s.room_name,
      checkIn: s.check_in,
      checkOut: s.check_out,
      amount: s.total || 0,
      rating,
      review,
    };
  });
  return json(result);
}

async function handleGuestCommunications(path, env) {
  const guestId = path.split('/')[2];

  // Pull from scheduled_messages (automated lifecycle messages)
  const scheduled = await env.DB.prepare(`
    SELECT sm.id, sm.message_type, sm.message_body, sm.send_at, sm.status, sm.sent_at
    FROM scheduled_messages sm
    WHERE sm.guest_id = ?
    ORDER BY sm.send_at DESC
    LIMIT 30
  `).bind(guestId).all();

  // Pull from sms_log for this guest's phone
  const guest = await env.DB.prepare('SELECT phone FROM guests WHERE id = ?').bind(guestId).first();
  let smsLogs = [];
  if (guest && guest.phone) {
    const logs = await env.DB.prepare(`
      SELECT id, phone, message_body, direction, status, created_at
      FROM sms_log
      WHERE phone = ?
      ORDER BY created_at DESC
      LIMIT 30
    `).bind(guest.phone).all();
    smsLogs = logs.results;
  }

  const typeMap = {
    pre_arrival: 'Pre-Arrival Info',
    check_in_day: 'Check-In Day',
    during_stay: 'During Stay',
    check_out: 'Check-Out',
  };

  // Merge both sources into CommunicationEntry format
  const entries = [];

  for (const sm of scheduled.results) {
    entries.push({
      id: `sm-${sm.id}`,
      type: 'sms',
      direction: 'outbound',
      subject: typeMap[sm.message_type] || sm.message_type,
      preview: (sm.message_body || '').substring(0, 120),
      timestamp: sm.sent_at || sm.send_at,
      sentiment: sm.status === 'sent' ? 'NEUTRAL' : sm.status === 'failed' ? 'NEGATIVE' : 'NEUTRAL',
    });
  }

  for (const log of smsLogs) {
    // Avoid duplicating scheduled messages already represented
    entries.push({
      id: `sms-${log.id}`,
      type: 'sms',
      direction: log.direction || 'outbound',
      subject: log.direction === 'inbound' ? 'Guest Message' : 'Sent SMS',
      preview: (log.message_body || '').substring(0, 120),
      timestamp: log.created_at,
      sentiment: log.direction === 'inbound' ? 'POSITIVE' : 'NEUTRAL',
    });
  }

  // Sort by timestamp descending and deduplicate by preview similarity
  entries.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));

  return json(entries.slice(0, 50));
}

// ═══════════════════════════════════════════════════════════════
// INVOICES
// ═══════════════════════════════════════════════════════════════

async function handleListInvoices(url, env) {
  const status = url.searchParams.get('status');
  let query = 'SELECT * FROM invoices';
  const params = [];
  if (status) { query += ' WHERE status = ?'; params.push(status); }
  query += ' ORDER BY created_at DESC LIMIT 100';
  const result = await env.DB.prepare(query).bind(...params).all();
  return json(result.results);
}

async function handleGetInvoice(path, env) {
  const id = path.split('/').pop();
  const invoice = await env.DB.prepare('SELECT * FROM invoices WHERE id = ?').bind(id).first();
  if (!invoice) return err('Invoice not found', 404);
  const items = await env.DB.prepare('SELECT * FROM invoice_items WHERE invoice_id = ?').bind(id).all();
  return json({ ...invoice, items: items.results });
}

async function handleCreateInvoice(request, env) {
  const body = await request.json();
  const { guest_name, guest_email, items, due_date, notes, status } = body;
  if (!guest_name || !items || items.length === 0) return err('guest_name and items required');

  const total = items.reduce((sum, item) => sum + (item.price * (item.qty || 1)), 0);
  const invoiceNum = 'RAH-' + Date.now().toString(36).toUpperCase();

  const result = await env.DB.prepare(
    'INSERT INTO invoices (invoice_number, guest_name, guest_email, total, status, issue_date, due_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(invoiceNum, guest_name, guest_email || '', total, status || 'draft', new Date().toISOString().split('T')[0], due_date || '', notes || '').run();

  const invoiceId = result.meta.last_row_id;

  // Insert line items
  for (const item of items) {
    await env.DB.prepare(
      'INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount) VALUES (?, ?, ?, ?, ?)'
    ).bind(invoiceId, item.description || item.name, item.qty || 1, item.price, (item.price * (item.qty || 1))).run();
  }

  log('info', 'Invoice created', { invoice_number: invoiceNum, total, guest: guest_name });
  return json({ id: invoiceId, invoice_number: invoiceNum, total, success: true }, 201);
}

async function handleUpdateInvoice(request, path, env) {
  const id = path.split('/').pop();
  const body = await request.json();
  const fields = [];
  const values = [];
  for (const [k, v] of Object.entries(body)) {
    if (['guest_name', 'guest_email', 'total', 'status', 'due_date', 'notes', 'paid_date'].includes(k)) {
      fields.push(`${k} = ?`);
      values.push(v);
    }
  }
  if (fields.length === 0) return err('No valid fields');
  values.push(id);
  await env.DB.prepare(`UPDATE invoices SET ${fields.join(', ')} WHERE id = ?`).bind(...values).run();
  return json({ success: true });
}

async function handleSendInvoice(path, env) {
  const id = path.match(/\/invoices\/(\d+)\/send/)[1];
  await env.DB.prepare("UPDATE invoices SET status = 'sent' WHERE id = ?").bind(id).run();
  // TODO: Email notification via Zoho SMTP
  return json({ success: true, message: 'Invoice marked as sent' });
}

// ═══════════════════════════════════════════════════════════════
// EXPENSES
// ═══════════════════════════════════════════════════════════════

async function handleListExpenses(url, env) {
  const month = url.searchParams.get('month'); // YYYY-MM
  let query = 'SELECT * FROM expenses';
  const params = [];
  if (month) { query += ' WHERE date LIKE ?'; params.push(month + '%'); }
  query += ' ORDER BY date DESC LIMIT 100';
  const result = await env.DB.prepare(query).bind(...params).all();
  return json(result.results);
}

async function handleCreateExpense(request, env) {
  const body = await request.json();
  const { category, description, amount, date, vendor, property, recurring } = body;
  if (!description || !amount) return err('description and amount required');

  const result = await env.DB.prepare(
    'INSERT INTO expenses (category, description, amount, date, vendor, property, recurring) VALUES (?, ?, ?, ?, ?, ?, ?)'
  ).bind(
    category || 'general',
    description,
    amount,
    date || new Date().toISOString().split('T')[0],
    vendor || '',
    property || '',
    recurring ? 1 : 0,
  ).run();

  return json({ id: result.meta.last_row_id, success: true }, 201);
}

async function handleDeleteExpense(path, env) {
  const id = path.split('/').pop();
  await env.DB.prepare('DELETE FROM expenses WHERE id = ?').bind(id).run();
  return json({ success: true });
}

// ═══════════════════════════════════════════════════════════════
// REVIEWS
// ═══════════════════════════════════════════════════════════════

async function handleListReviews(env) {
  const result = await env.DB.prepare('SELECT * FROM reviews ORDER BY created_at DESC').all();
  return json(result.results);
}

async function handleCreateReview(request, env) {
  const body = await request.json();
  const { guest_name, rating, text, source, response } = body;
  if (!guest_name || !rating) return err('guest_name and rating required');

  const result = await env.DB.prepare(
    'INSERT INTO reviews (guest_name, rating, text, source, response) VALUES (?, ?, ?, ?, ?)'
  ).bind(guest_name, rating, text || '', source || 'direct', response || '').run();

  return json({ id: result.meta.last_row_id, success: true }, 201);
}

// ═══════════════════════════════════════════════════════════════
// PROPERTIES
// ═══════════════════════════════════════════════════════════════

async function handleListProperties(env) {
  const result = await env.DB.prepare('SELECT * FROM properties ORDER BY id').all();
  return json(result.results);
}

async function handleCreateProperty(request, env) {
  const body = await request.json();
  const { name, address, bedrooms, bathrooms, max_guests, nightly_rate, status, description } = body;
  if (!name) return err('name required');

  const result = await env.DB.prepare(
    'INSERT INTO properties (name, address, bedrooms, bathrooms, max_guests, nightly_rate, status, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(name, address || '', bedrooms || 0, bathrooms || 0, max_guests || 2, nightly_rate || 85, status || 'active', description || '').run();

  return json({ id: result.meta.last_row_id, success: true }, 201);
}

async function handleUpdateProperty(request, path, env) {
  const id = path.split('/').pop();
  const body = await request.json();
  const fields = [];
  const values = [];
  for (const [k, v] of Object.entries(body)) {
    if (['name', 'address', 'bedrooms', 'bathrooms', 'max_guests', 'nightly_rate', 'status', 'description'].includes(k)) {
      fields.push(`${k} = ?`);
      values.push(v);
    }
  }
  if (fields.length === 0) return err('No valid fields');
  values.push(id);
  await env.DB.prepare(`UPDATE properties SET ${fields.join(', ')} WHERE id = ?`).bind(...values).run();
  return json({ success: true });
}

// ═══════════════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════════════

async function handleGetSettings(env) {
  const result = await env.DB.prepare('SELECT key, value FROM settings').all();
  const settings = {};
  for (const row of result.results) {
    try { settings[row.key] = JSON.parse(row.value); } catch { settings[row.key] = row.value; }
  }
  return json(settings);
}

async function handleSaveSettings(request, env) {
  const body = await request.json();
  for (const [key, value] of Object.entries(body)) {
    const val = typeof value === 'string' ? value : JSON.stringify(value);
    await env.DB.prepare(
      'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = datetime(\'now\')'
    ).bind(key, val, val).run();
  }
  return json({ success: true });
}

// ═══════════════════════════════════════════════════════════════
// WEATHER (Midland, TX via wttr.in — free, no key needed)
// ═══════════════════════════════════════════════════════════════

async function handleWeather(env) {
  const cached = await env.CACHE.get('weather', 'json');
  if (cached) return json(cached);

  try {
    const resp = await fetch('https://wttr.in/Midland,TX?format=j1', {
      headers: { 'User-Agent': 'rah-api/1.0' },
    });
    if (!resp.ok) return json({ error: 'Weather unavailable' });

    const data = await resp.json();
    const current = data.current_condition?.[0] || {};
    const weather = {
      temp_f: current.temp_F || '--',
      condition: current.weatherDesc?.[0]?.value || 'Unknown',
      humidity: current.humidity || '--',
      wind_mph: current.windspeedMiles || '--',
      wind_dir: current.winddir16Point || '',
      feels_like: current.FeelsLikeF || '--',
      uv: current.uvIndex || '--',
      forecast: (data.weather || []).slice(0, 3).map(d => ({
        date: d.date,
        high: d.maxtempF,
        low: d.mintempF,
        condition: d.hourly?.[4]?.weatherDesc?.[0]?.value || '',
      })),
    };

    await env.CACHE.put('weather', JSON.stringify(weather), { expirationTtl: 1800 });
    return json(weather);
  } catch (e) {
    log('warn', 'Weather fetch failed', { error: e.message });
    return json({ temp_f: '--', condition: 'Unavailable', humidity: '--', wind_mph: '--' });
  }
}

// ═══════════════════════════════════════════════════════════════
// AUTOMATED MESSAGING ENDPOINTS
// ═══════════════════════════════════════════════════════════════

async function handleListMessages(url, env) {
  const params = new URL(url).searchParams;
  const bookingId = params.get('booking_id');
  const status = params.get('status');
  let query = 'SELECT * FROM scheduled_messages';
  const binds = [];
  const conditions = [];
  if (bookingId) { conditions.push('booking_id = ?'); binds.push(bookingId); }
  if (status) { conditions.push('status = ?'); binds.push(status); }
  if (conditions.length > 0) query += ' WHERE ' + conditions.join(' AND ');
  query += ' ORDER BY send_at ASC';
  const result = await env.DB.prepare(query).bind(...binds).all();
  return json(result.results);
}

async function handleMessageStats(env) {
  const stats = await env.DB.prepare(`
    SELECT
      (SELECT COUNT(*) FROM scheduled_messages WHERE status = 'pending') as pending,
      (SELECT COUNT(*) FROM scheduled_messages WHERE status = 'sent') as sent,
      (SELECT COUNT(*) FROM scheduled_messages WHERE status = 'failed') as failed,
      (SELECT COUNT(*) FROM scheduled_messages WHERE status = 'cancelled') as cancelled,
      (SELECT COUNT(*) FROM sms_log) as total_sms_sent
  `).first();
  return json(stats);
}

async function handleCancelMessage(path, env) {
  const id = path.split('/')[2];
  await env.DB.prepare("UPDATE scheduled_messages SET status = 'cancelled' WHERE id = ? AND status = 'pending'").bind(id).run();
  return json({ success: true });
}

async function handleSendNow(request, env) {
  const body = await request.json();
  const { phone, message } = body;
  if (!phone || !message) return err('phone and message required');
  const result = await sendSms(phone, message, env);
  if (result.success) {
    await env.DB.prepare(
      "INSERT INTO sms_log (phone, message_body, direction, twilio_sid, status) VALUES (?, ?, 'outbound', ?, 'sent')"
    ).bind(phone, message, result.sid || '').run();
  }
  return json(result);
}

// ═══════════════════════════════════════════════════════════════
// PAYPAL INTEGRATION — 3% Surcharge on Guest Invoices
// ═══════════════════════════════════════════════════════════════

const PAYPAL_SURCHARGE_PCT = 3.0; // 3% processing fee passed to guest

async function paypalProxy(path, method, body, env) {
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-Echo-API-Key': env.ECHO_API_KEY || 'echo-omega-prime-forge-x-2026',
      'X-Tenant': 'rah-midland',
    },
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const resp = await env.PAYPAL.fetch(`https://paypal${path}`, opts);
    const data = await resp.json().catch(() => ({}));
    return { ok: resp.ok, status: resp.status, data };
  } catch (e) {
    log('error', 'PayPal proxy error', { path, error: e.message });
    return { ok: false, status: 500, data: { error: e.message } };
  }
}

function calculateSurcharge(subtotal) {
  const surcharge = Math.round(subtotal * PAYPAL_SURCHARGE_PCT) / 100;
  return { surcharge, total: subtotal + surcharge, pct: PAYPAL_SURCHARGE_PCT };
}

async function handlePayPalConfig(env) {
  const config = await env.CACHE.get('paypal_config', 'json') || {
    surcharge_pct: PAYPAL_SURCHARGE_PCT,
    auto_send: true,
    business_name: env.PROPERTY_NAME || 'Right at Home BnB',
    business_email: env.OWNER_EMAIL || 'steven@rah-midland.com',
  };
  return json(config);
}

async function handleSavePayPalConfig(request, env) {
  const body = await request.json();
  const existing = await env.CACHE.get('paypal_config', 'json') || {};
  const updated = { ...existing, ...body };
  await env.CACHE.put('paypal_config', JSON.stringify(updated));
  return json({ success: true, config: updated });
}

async function handleCreatePayPalInvoice(path, env) {
  const invoiceId = path.match(/\/invoices\/(\d+)\/paypal/)[1];
  const invoice = await env.DB.prepare('SELECT * FROM invoices WHERE id = ?').bind(invoiceId).first();
  if (!invoice) return err('Invoice not found', 404);
  if (invoice.paypal_invoice_id) return err('PayPal invoice already created', 409);

  // Get line items
  const items = await env.DB.prepare('SELECT * FROM invoice_items WHERE invoice_id = ?').bind(invoiceId).all();
  if (!items.results.length) return err('Invoice has no line items', 400);

  // Calculate surcharge
  const subtotal = parseFloat(invoice.total) || items.results.reduce((s, i) => s + (i.amount || i.unit_price * i.quantity), 0);
  const { surcharge, total } = calculateSurcharge(subtotal);

  // Build PayPal invoice items (original items + surcharge)
  const paypalItems = items.results.map(item => ({
    name: item.description || 'Service',
    quantity: item.quantity || 1,
    unit_price: parseFloat(item.unit_price || item.amount),
    description: item.description || '',
  }));

  // Add surcharge line item
  if (surcharge > 0) {
    paypalItems.push({
      name: `Processing Fee (${PAYPAL_SURCHARGE_PCT}%)`,
      quantity: 1,
      unit_price: surcharge,
      description: 'PayPal processing surcharge',
    });
  }

  const config = await env.CACHE.get('paypal_config', 'json') || {};
  const autoSend = config.auto_send !== false;

  // Create via echo-paypal Worker
  const result = await paypalProxy('/invoices', 'POST', {
    customer_email: invoice.guest_email,
    customer_name: invoice.guest_name,
    items: paypalItems,
    note: `Invoice ${invoice.invoice_number} — ${env.PROPERTY_NAME || 'Right at Home BnB'}`,
    due_date: invoice.due_date || undefined,
    auto_send: autoSend,
  }, env);

  if (!result.ok) {
    log('error', 'PayPal invoice creation failed', { invoiceId, error: result.data });
    return json({ success: false, error: 'PayPal invoice creation failed', details: result.data }, result.status);
  }

  const ppId = result.data.invoice_id || '';
  const ppStatus = autoSend ? 'SENT' : 'DRAFT';

  await env.DB.prepare(
    `UPDATE invoices SET paypal_invoice_id = ?, paypal_status = ?, surcharge_amount = ?,
     surcharge_pct = ?, total_with_surcharge = ?, status = CASE WHEN status = 'draft' THEN 'sent' ELSE status END
     WHERE id = ?`
  ).bind(ppId, ppStatus, surcharge, PAYPAL_SURCHARGE_PCT, total, invoiceId).run();

  log('info', 'PayPal invoice created', { invoiceId, paypal_id: ppId, subtotal, surcharge, total });
  await ingestToBrain(env, `RAH PAYPAL: Invoice ${invoice.invoice_number} sent to ${invoice.guest_name} (${invoice.guest_email}) — $${subtotal} + $${surcharge} surcharge = $${total}`, 7, ['paypal', 'invoice']);

  return json({
    success: true,
    paypal_invoice_id: ppId,
    subtotal,
    surcharge,
    surcharge_pct: PAYPAL_SURCHARGE_PCT,
    total,
    status: ppStatus,
  });
}

async function handlePaymentLink(path, env) {
  const invoiceId = path.match(/\/invoices\/(\d+)\/payment-link/)[1];
  const invoice = await env.DB.prepare('SELECT * FROM invoices WHERE id = ?').bind(invoiceId).first();
  if (!invoice) return err('Invoice not found', 404);

  const subtotal = parseFloat(invoice.total) || 0;
  const { surcharge, total } = calculateSurcharge(subtotal);

  const result = await paypalProxy('/payment-links', 'POST', {
    amount: total,
    description: `${invoice.invoice_number} — ${invoice.guest_name || 'Guest'} — ${env.PROPERTY_NAME || 'Right at Home BnB'}`,
  }, env);

  if (!result.ok) {
    return json({ success: false, error: 'Payment link creation failed', details: result.data }, result.status);
  }

  const paymentUrl = result.data.payment_url || '';
  await env.DB.prepare(
    'UPDATE invoices SET payment_link = ?, surcharge_amount = ?, total_with_surcharge = ? WHERE id = ?'
  ).bind(paymentUrl, surcharge, total, invoiceId).run();

  log('info', 'Payment link created', { invoiceId, total, url: paymentUrl });

  // Optionally text the payment link to the guest
  if (invoice.guest_email) {
    const guest = await env.DB.prepare('SELECT phone FROM guests WHERE email = ?').bind(invoice.guest_email).first();
    if (guest?.phone && paymentUrl) {
      const smsBody = `Hi ${invoice.guest_name || 'there'}! Here's your payment link for Right at Home BnB ($${total.toFixed(2)}): ${paymentUrl}`;
      await sendSms(guest.phone, smsBody, env).catch(e => log('warn', 'Failed to SMS payment link', { error: e.message }));
    }
  }

  return json({
    success: true,
    payment_url: paymentUrl,
    order_id: result.data.order_id,
    subtotal,
    surcharge,
    total,
  });
}

async function handlePayPalStatus(path, env) {
  const invoiceId = path.match(/\/invoices\/(\d+)\/paypal-status/)[1];
  const invoice = await env.DB.prepare('SELECT paypal_invoice_id, paypal_status, payment_link, surcharge_amount, total_with_surcharge FROM invoices WHERE id = ?').bind(invoiceId).first();
  if (!invoice) return err('Invoice not found', 404);
  if (!invoice.paypal_invoice_id) return json({ paypal_connected: false });

  // Fetch live status from PayPal
  const result = await paypalProxy(`/invoices/${invoice.paypal_invoice_id}`, 'GET', null, env);
  if (result.ok && result.data) {
    const liveStatus = result.data.status || invoice.paypal_status;
    if (liveStatus !== invoice.paypal_status) {
      await env.DB.prepare('UPDATE invoices SET paypal_status = ? WHERE id = ?').bind(liveStatus, invoiceId).run();
    }
    return json({
      paypal_connected: true,
      paypal_invoice_id: invoice.paypal_invoice_id,
      status: liveStatus,
      payment_link: invoice.payment_link,
      surcharge: invoice.surcharge_amount,
      total_with_surcharge: invoice.total_with_surcharge,
      details: result.data,
    });
  }

  return json({
    paypal_connected: true,
    paypal_invoice_id: invoice.paypal_invoice_id,
    status: invoice.paypal_status,
    payment_link: invoice.payment_link,
    surcharge: invoice.surcharge_amount,
    total_with_surcharge: invoice.total_with_surcharge,
  });
}

async function handlePayPalTransactions(url, env) {
  const limit = url.searchParams.get('limit') || '20';
  const result = await paypalProxy(`/transactions?limit=${limit}`, 'GET', null, env);
  if (!result.ok) return json({ transactions: [], error: 'Failed to fetch' }, result.status);
  return json(result.data);
}

async function handlePayPalStats(env) {
  const payments = await env.DB.prepare(`
    SELECT
      COUNT(*) as total_payments,
      COALESCE(SUM(amount), 0) as total_collected,
      COALESCE(SUM(CASE WHEN created_at >= date('now', '-30 days') THEN amount ELSE 0 END), 0) as last_30_days,
      COALESCE(SUM(CASE WHEN created_at >= date('now', '-7 days') THEN amount ELSE 0 END), 0) as last_7_days
    FROM payments WHERE status = 'completed'
  `).first();

  const invoiceStats = await env.DB.prepare(`
    SELECT
      COUNT(CASE WHEN paypal_invoice_id != '' THEN 1 END) as paypal_invoices,
      COALESCE(SUM(surcharge_amount), 0) as total_surcharges,
      COALESCE(SUM(total_with_surcharge), 0) as total_billed,
      COUNT(CASE WHEN paypal_status = 'PAID' THEN 1 END) as paid_count,
      COUNT(CASE WHEN paypal_status = 'SENT' THEN 1 END) as sent_count
    FROM invoices WHERE paypal_invoice_id != ''
  `).first();

  return json({
    payments,
    invoices: invoiceStats,
    surcharge_pct: PAYPAL_SURCHARGE_PCT,
  });
}

async function handleListPayments(url, env) {
  const invoiceId = url.searchParams.get('invoice_id');
  let query = 'SELECT p.*, i.invoice_number FROM payments p LEFT JOIN invoices i ON p.invoice_id = i.id';
  const params = [];
  if (invoiceId) { query += ' WHERE p.invoice_id = ?'; params.push(invoiceId); }
  query += ' ORDER BY p.created_at DESC LIMIT 100';
  const result = await env.DB.prepare(query).bind(...params).all();
  return json(result.results);
}

async function handleRecordPayment(request, env) {
  const body = await request.json();
  const { invoice_id, amount, method, payer_email, notes, paypal_transaction_id } = body;
  if (!invoice_id || !amount) return err('invoice_id and amount required');

  await env.DB.prepare(
    'INSERT INTO payments (invoice_id, paypal_transaction_id, amount, method, status, payer_email, notes) VALUES (?, ?, ?, ?, ?, ?, ?)'
  ).bind(invoice_id, paypal_transaction_id || '', amount, method || 'paypal', 'completed', payer_email || '', notes || '').run();

  // Update invoice paid amount
  const totalPaid = await env.DB.prepare('SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE invoice_id = ?').bind(invoice_id).first();
  await env.DB.prepare("UPDATE invoices SET paid_amount = ?, payment_method = ?, status = CASE WHEN ? >= total THEN 'paid' ELSE status END WHERE id = ?")
    .bind(totalPaid.total, method || 'paypal', totalPaid.total, invoice_id).run();

  log('info', 'Payment recorded', { invoice_id, amount, method });

  await createNotification(env, 'payment', 'Payment Received',
    `$${parseFloat(amount).toFixed(2)} received via ${method || 'PayPal'} for Invoice #${invoice_id}`,
    'success', '/finance', { invoice_id, amount, method: method || 'paypal' });

  return json({ success: true }, 201);
}

// ═══════════════════════════════════════════════════════════════
// CHAT ENDPOINTS
// ═══════════════════════════════════════════════════════════════

async function handlePublicChat(request, env) {
  const body = await request.json();
  const result = await handleChat(body.messages || [], env, true);
  return json(result);
}

async function handleOwnerChat(request, env) {
  const body = await request.json();
  const result = await handleChat(body.messages || [], env, false);
  return json(result);
}

// ═══════════════════════════════════════════════════════════════
// INQUIRIES (public contact form)
// ═══════════════════════════════════════════════════════════════

async function handleInquiry(request, env, ctx) {
  const body = await request.json();
  const { name, email, phone, dates, message } = body;
  if (!name || !email) return err('name and email required');

  await env.DB.prepare(
    'INSERT INTO inquiries (name, email, phone, dates, message) VALUES (?, ?, ?, ?, ?)'
  ).bind(name, email, phone || '', dates || '', message || '').run();

  // Fire-and-forget: notify via brain
  ctx.waitUntil(
    ingestToBrain(env, `RAH INQUIRY: ${name} (${email}) wants to stay ${dates || 'TBD'}. Message: ${message || 'none'}`, 7, ['inquiry', 'lead'])
  );

  log('info', 'Inquiry received', { name, email, dates });

  await createNotification(env, 'booking', 'New Inquiry',
    `${name} (${email}) wants to stay ${dates || 'TBD'}`,
    'warning', '/bookings', { name, email, dates });

  return json({ success: true, message: 'Inquiry received! Steven will get back to you shortly.' }, 201);
}

// ═══════════════════════════════════════════════════════════════
// GUEST ROUTES (authenticated but not owner)
// ═══════════════════════════════════════════════════════════════

async function handleGuestBookings(user, env) {
  const guest = await env.DB.prepare('SELECT id FROM guests WHERE email = ? OR firebase_uid = ?')
    .bind(user.email, user.uid).first();
  if (!guest) return json([]);
  const result = await env.DB.prepare(
    'SELECT * FROM bookings WHERE guest_id = ? ORDER BY check_in DESC'
  ).bind(guest.id).all();
  return json(result.results);
}

async function handleGuestInvoices(user, env) {
  const result = await env.DB.prepare(
    'SELECT * FROM invoices WHERE guest_email = ? ORDER BY created_at DESC'
  ).bind(user.email).all();
  return json(result.results);
}

// ═══════════════════════════════════════════════════════════════
// SMART LOCK HANDLERS
// ═══════════════════════════════════════════════════════════════

// GET /locks — List all registered locks with status + active code count
async function handleListLocks(env) {
  const locks = await env.DB.prepare(`
    SELECT sl.*,
      (SELECT COUNT(*) FROM access_codes ac WHERE ac.lock_id = sl.id AND ac.is_active = 1) as active_codes,
      (SELECT COUNT(*) FROM lock_activity la WHERE la.lock_id = sl.id) as total_events
    FROM smart_locks sl ORDER BY sl.name
  `).all();
  return json(locks.results);
}

// POST /locks/register — Register a new Arpha D280W smart lock
async function handleRegisterLock(request, env) {
  const body = await request.json();
  const { name, location, tuya_device_id } = body;
  if (!name || !tuya_device_id) return err('name and tuya_device_id required');

  // Verify device exists on Tuya
  const device = await tuyaGetDevice(tuya_device_id, env);
  if (!device.success) {
    return err(`Tuya device not found or inaccessible: ${device.msg || 'unknown error'}`, 404);
  }

  try {
    await env.DB.prepare(
      'INSERT INTO smart_locks (name, location, tuya_device_id, model, status) VALUES (?, ?, ?, ?, ?)'
    ).bind(
      name,
      location || device.result?.name || '',
      tuya_device_id,
      device.result?.product_name || 'Arpha D280W',
      device.result?.online ? 'online' : 'offline'
    ).run();

    const lock = await env.DB.prepare('SELECT * FROM smart_locks WHERE tuya_device_id = ?').bind(tuya_device_id).first();
    log('info', 'Lock registered', { name, tuya_device_id });
    return json(lock, 201);
  } catch (e) {
    if (e.message?.includes('UNIQUE')) return err('Lock with that Tuya device ID already registered', 409);
    throw e;
  }
}

// GET /locks/:id — Get lock details + recent activity
async function handleGetLock(path, env) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT * FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  const [codes, activity] = await Promise.all([
    env.DB.prepare('SELECT * FROM access_codes WHERE lock_id = ? AND is_active = 1 ORDER BY created_at DESC').bind(lockId).all(),
    env.DB.prepare('SELECT * FROM lock_activity WHERE lock_id = ? ORDER BY recorded_at DESC LIMIT 20').bind(lockId).all(),
  ]);

  return json({ ...lock, codes: codes.results, recent_activity: activity.results });
}

// POST /locks/:id/guest-code — Generate a guest code linked to a booking
async function handleGuestCode(request, path, env, ctx) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT * FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  const body = await request.json();
  const { booking_id, guest_name, guest_phone, check_in, check_out } = body;
  if (!check_in || !check_out) return err('check_in and check_out required');

  // Generate code
  const code = generateCode(6);
  const effectiveTime = check_in.includes('T') ? check_in : `${check_in}T15:00:00`;
  const expiryTime = check_out.includes('T') ? check_out : `${check_out}T11:30:00`;
  const codeName = `Guest: ${guest_name || 'Guest'} (${check_in.split('T')[0]})`;

  // Create on Tuya
  const tuyaResult = await tuyaCreateTempPassword(lock.tuya_device_id, env, {
    name: codeName, code, effectiveTime, expiryTime,
  });

  if (!tuyaResult.success) {
    return err(`Tuya API error: ${tuyaResult.msg || 'Failed to create password'}`, 502);
  }

  // Store in D1
  await env.DB.prepare(
    'INSERT INTO access_codes (lock_id, tuya_password_id, code, name, code_type, holder_name, holder_phone, booking_id, effective_time, expiry_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(
    lockId, tuyaResult.result?.pwd_id || '', code, codeName, 'guest',
    guest_name || '', guest_phone || '', booking_id || null,
    effectiveTime, expiryTime
  ).run();

  const codeRecord = await env.DB.prepare('SELECT * FROM access_codes WHERE lock_id = ? AND code = ? AND is_active = 1 ORDER BY id DESC LIMIT 1').bind(lockId, code).first();

  ctx.waitUntil(
    ingestToBrain(env, `RAH LOCKS: Guest code generated for ${guest_name || 'guest'} on lock "${lock.name}" (${check_in} to ${check_out})`, 7, ['locks', 'guest-code'])
  );

  log('info', 'Guest code created', { lock: lock.name, guest: guest_name, booking_id });
  return json({ ...codeRecord, lock_name: lock.name }, 201);
}

// POST /locks/:id/worker-code — Generate a persistent worker code
async function handleWorkerCode(request, path, env, ctx) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT * FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  const body = await request.json();
  const { worker_id, worker_name, worker_phone } = body;
  if (!worker_id) return err('worker_id required');

  // Check worker exists
  const worker = await env.DB.prepare('SELECT * FROM workers WHERE id = ? AND is_active = 1').bind(worker_id).first();
  if (!worker) return err('Worker not found or inactive', 404);

  // Revoke any existing active code for this worker on this lock
  const existingCodes = await env.DB.prepare(
    "SELECT ac.*, sl.tuya_device_id FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.lock_id = ? AND ac.holder_id = ? AND ac.code_type = 'worker' AND ac.is_active = 1"
  ).bind(lockId, worker_id).all();
  for (const old of existingCodes.results) {
    if (old.tuya_password_id) {
      await tuyaDeletePassword(old.tuya_device_id, old.tuya_password_id, env).catch(() => {});
    }
    await env.DB.prepare("UPDATE access_codes SET is_active = 0, revoked_at = datetime('now'), revoke_reason = 'replaced' WHERE id = ?").bind(old.id).run();
  }

  // Generate persistent code (no expiry — good until revoked)
  const code = generateCode(6);
  const effectiveTime = new Date().toISOString();
  const codeName = `Worker: ${worker.name} (${worker.role})`;

  const tuyaResult = await tuyaCreateTempPassword(lock.tuya_device_id, env, {
    name: codeName, code, effectiveTime, expiryTime: null,
  });

  if (!tuyaResult.success) {
    return err(`Tuya API error: ${tuyaResult.msg || 'Failed to create password'}`, 502);
  }

  await env.DB.prepare(
    'INSERT INTO access_codes (lock_id, tuya_password_id, code, name, code_type, holder_id, holder_name, holder_phone, effective_time, expiry_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(
    lockId, tuyaResult.result?.pwd_id || '', code, codeName, 'worker',
    worker.id, worker.name, worker.phone || worker_phone || '',
    effectiveTime, null
  ).run();

  // Update worker record with code reference
  const codeRecord = await env.DB.prepare('SELECT id FROM access_codes WHERE lock_id = ? AND holder_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1').bind(lockId, worker.id).first();
  if (codeRecord) {
    await env.DB.prepare('UPDATE workers SET code_id = ? WHERE id = ?').bind(codeRecord.id, worker.id).run();
  }

  ctx.waitUntil(
    ingestToBrain(env, `RAH LOCKS: Worker code generated for ${worker.name} (${worker.role}) on lock "${lock.name}"`, 7, ['locks', 'worker-code'])
  );

  log('info', 'Worker code created', { lock: lock.name, worker: worker.name, role: worker.role });
  return json({ code, lock_name: lock.name, worker_name: worker.name, worker_role: worker.role }, 201);
}

// POST /locks/:id/steven-code — Set Steven's permanent owner code
async function handleStevenCode(request, path, env, ctx) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT * FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  const body = await request.json();
  const code = body.code || generateCode(6);

  // Revoke any existing owner codes on this lock
  const existingOwner = await env.DB.prepare(
    "SELECT ac.*, sl.tuya_device_id FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.lock_id = ? AND ac.code_type = 'owner' AND ac.is_active = 1"
  ).bind(lockId).all();
  for (const old of existingOwner.results) {
    if (old.tuya_password_id) {
      await tuyaDeletePassword(old.tuya_device_id, old.tuya_password_id, env).catch(() => {});
    }
    await env.DB.prepare("UPDATE access_codes SET is_active = 0, revoked_at = datetime('now'), revoke_reason = 'replaced' WHERE id = ?").bind(old.id).run();
  }

  // Create permanent code on Tuya (no expiry)
  const effectiveTime = new Date().toISOString();
  const codeName = "Owner: Steven";

  const tuyaResult = await tuyaCreateTempPassword(lock.tuya_device_id, env, {
    name: codeName, code, effectiveTime, expiryTime: null,
  });

  if (!tuyaResult.success) {
    return err(`Tuya API error: ${tuyaResult.msg || 'Failed to create password'}`, 502);
  }

  await env.DB.prepare(
    'INSERT INTO access_codes (lock_id, tuya_password_id, code, name, code_type, holder_name, effective_time, expiry_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(
    lockId, tuyaResult.result?.pwd_id || '', code, codeName, 'owner',
    'Steven', effectiveTime, null
  ).run();

  // Save to settings for quick reference
  await env.DB.prepare("INSERT OR REPLACE INTO settings (key, value) VALUES ('steven_lock_code', ?)").bind(JSON.stringify(code)).run();

  ctx.waitUntil(
    ingestToBrain(env, `RAH LOCKS: Steven's permanent code set on lock "${lock.name}"`, 8, ['locks', 'owner-code'])
  );

  log('info', 'Steven code set', { lock: lock.name });
  return json({ code, lock_name: lock.name, holder: 'Steven', type: 'owner', permanent: true }, 201);
}

// GET /locks/:id/codes — List access codes (filter by type, active status)
async function handleListCodes(path, url, env) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT id FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  const codeType = url.searchParams.get('type'); // 'guest', 'worker', 'owner'
  const active = url.searchParams.get('active'); // '0' or '1'

  let query = 'SELECT * FROM access_codes WHERE lock_id = ?';
  const params = [lockId];

  if (codeType) {
    query += ' AND code_type = ?';
    params.push(codeType);
  }
  if (active !== null && active !== undefined && active !== '') {
    query += ' AND is_active = ?';
    params.push(parseInt(active));
  }
  query += ' ORDER BY created_at DESC';

  const stmt = env.DB.prepare(query);
  const result = await (params.length === 1 ? stmt.bind(params[0]) :
    params.length === 2 ? stmt.bind(params[0], params[1]) :
    stmt.bind(params[0], params[1], params[2])).all();

  return json(result.results);
}

// POST /locks/:id/codes/:codeId/revoke — Revoke a specific access code
async function handleRevokeCode(path, env, ctx) {
  const parts = path.split('/');
  const lockId = parseInt(parts[2]);
  const codeId = parseInt(parts[4]);

  const code = await env.DB.prepare(
    'SELECT ac.*, sl.tuya_device_id FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.id = ? AND ac.lock_id = ?'
  ).bind(codeId, lockId).first();

  if (!code) return err('Code not found', 404);
  if (!code.is_active) return err('Code already revoked');

  // Delete from Tuya
  if (code.tuya_password_id) {
    const delResult = await tuyaDeletePassword(code.tuya_device_id, code.tuya_password_id, env);
    if (!delResult.success) {
      log('warn', 'Tuya password delete may have failed', { code_id: codeId, msg: delResult.msg });
    }
  }

  // Mark inactive in D1
  await env.DB.prepare(
    "UPDATE access_codes SET is_active = 0, revoked_at = datetime('now'), revoke_reason = 'manual' WHERE id = ?"
  ).bind(codeId).run();

  // If worker code, clear worker's code_id reference
  if (code.code_type === 'worker' && code.holder_id) {
    await env.DB.prepare('UPDATE workers SET code_id = NULL WHERE id = ? AND code_id = ?').bind(code.holder_id, codeId).run();
  }

  ctx.waitUntil(
    ingestToBrain(env, `RAH LOCKS: Code revoked — ${code.name} (${code.code_type}) on lock ${lockId}`, 6, ['locks', 'revoke'])
  );

  log('info', 'Code revoked', { code_id: codeId, type: code.code_type, holder: code.holder_name });
  return json({ success: true, message: 'Code revoked', code_id: codeId });
}

// GET /locks/:id/activity — Get lock activity logs with filtering
async function handleLockActivity(path, url, env) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT id FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  const limit = Math.min(parseInt(url.searchParams.get('limit') || '50'), 200);
  const offset = parseInt(url.searchParams.get('offset') || '0');
  const eventType = url.searchParams.get('event_type');
  const since = url.searchParams.get('since'); // ISO date

  let query = 'SELECT * FROM lock_activity WHERE lock_id = ?';
  const params = [lockId];

  if (eventType) {
    query += ' AND event_type = ?';
    params.push(eventType);
  }
  if (since) {
    query += ' AND recorded_at >= ?';
    params.push(since);
  }

  query += ' ORDER BY recorded_at DESC LIMIT ? OFFSET ?';
  params.push(limit, offset);

  // D1 doesn't support spread bind, so build dynamically
  let stmt = env.DB.prepare(query);
  if (params.length === 4) stmt = stmt.bind(params[0], params[1], params[2], params[3]);
  else if (params.length === 5) stmt = stmt.bind(params[0], params[1], params[2], params[3], params[4]);
  else stmt = stmt.bind(params[0], params[1], params[2]);

  const result = await stmt.all();

  // Get total count for pagination
  let countQuery = 'SELECT COUNT(*) as total FROM lock_activity WHERE lock_id = ?';
  const countParams = [lockId];
  if (eventType) { countQuery += ' AND event_type = ?'; countParams.push(eventType); }
  if (since) { countQuery += ' AND recorded_at >= ?'; countParams.push(since); }
  let countStmt = env.DB.prepare(countQuery);
  if (countParams.length === 1) countStmt = countStmt.bind(countParams[0]);
  else if (countParams.length === 2) countStmt = countStmt.bind(countParams[0], countParams[1]);
  else countStmt = countStmt.bind(countParams[0], countParams[1], countParams[2]);
  const total = await countStmt.first();

  return json({ results: result.results, total: total?.total || 0, limit, offset });
}

// POST /locks/:id/sync-activity — Manually trigger activity sync from Tuya
async function handleSyncActivity(path, env) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT * FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  let synced = 0;
  const logs = await tuyaGetOpenLogs(lock.tuya_device_id, env, 1, 50);
  if (!logs.success) return err(`Tuya API error: ${logs.msg || 'Failed to fetch logs'}`, 502);

  if (logs.result?.records) {
    for (const record of logs.result.records) {
      const recordId = String(record.id || record.record_id || '');
      const existing = await env.DB.prepare('SELECT id FROM lock_activity WHERE tuya_record_id = ?').bind(recordId).first();
      if (existing) continue;

      await env.DB.prepare(
        'INSERT INTO lock_activity (lock_id, event_type, unlock_method, user_name, tuya_record_id, details, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
      ).bind(
        lock.id,
        record.status === 'unlock' ? 'unlock' : (record.status || 'unknown'),
        record.unlock_name || record.dp_code || '',
        record.nick_name || record.user_name || '',
        recordId,
        JSON.stringify(record),
        new Date((record.update_time || record.create_time || Date.now()) * 1000).toISOString()
      ).run();
      synced++;
    }
  }

  // Also refresh device status
  const deviceInfo = await tuyaGetDevice(lock.tuya_device_id, env);
  if (deviceInfo.success && deviceInfo.result) {
    await env.DB.prepare("UPDATE smart_locks SET status = ?, last_seen = datetime('now') WHERE id = ?")
      .bind(deviceInfo.result.online ? 'online' : 'offline', lock.id).run();
  }

  log('info', 'Activity synced', { lock: lock.name, new_records: synced });
  return json({ success: true, lock: lock.name, new_records: synced, total_fetched: logs.result?.records?.length || 0 });
}

// POST /locks/:id/unlock — Remote unlock via Tuya API
async function handleRemoteUnlock(path, env, ctx) {
  const lockId = parseInt(path.split('/')[2]);
  const lock = await env.DB.prepare('SELECT * FROM smart_locks WHERE id = ?').bind(lockId).first();
  if (!lock) return err('Lock not found', 404);

  // Send unlock command via Tuya
  const result = await tuyaRequest('POST', `/v1.0/devices/${lock.tuya_device_id}/door-lock/password-free/open-door`, env);

  if (!result.success) {
    return err(`Remote unlock failed: ${result.msg || 'Tuya API error'}`, 502);
  }

  // Log the remote unlock
  await env.DB.prepare(
    "INSERT INTO lock_activity (lock_id, event_type, unlock_method, user_name, details, recorded_at) VALUES (?, 'unlock', 'remote', 'Owner (Remote)', 'Remote unlock via API', datetime('now'))"
  ).bind(lockId).run();

  ctx.waitUntil(
    ingestToBrain(env, `RAH LOCKS: Remote unlock triggered on "${lock.name}"`, 8, ['locks', 'remote-unlock'])
  );

  log('info', 'Remote unlock', { lock: lock.name });
  return json({ success: true, message: `Lock "${lock.name}" unlocked remotely` });
}

// ═══════════════════════════════════════════════════════════════
// WORKER (CLEANER/MAINTENANCE) HANDLERS
// ═══════════════════════════════════════════════════════════════

// GET /workers — List all registered workers
async function handleListWorkers(env) {
  const workers = await env.DB.prepare(`
    SELECT w.*,
      (SELECT ac.code FROM access_codes ac WHERE ac.id = w.code_id AND ac.is_active = 1) as active_code,
      (SELECT ac.lock_id FROM access_codes ac WHERE ac.id = w.code_id AND ac.is_active = 1) as code_lock_id,
      (SELECT sl.name FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.id = w.code_id AND ac.is_active = 1) as code_lock_name
    FROM workers w ORDER BY w.is_active DESC, w.name
  `).all();
  return json(workers.results);
}

// POST /workers — Register a new worker + auto-generate codes for all locks
async function handleRegisterWorker(request, env, ctx) {
  const body = await request.json();
  const { name, phone, email, role, notes } = body;
  if (!name) return err('name required');

  // Insert worker
  await env.DB.prepare(
    'INSERT INTO workers (name, phone, email, role, notes) VALUES (?, ?, ?, ?, ?)'
  ).bind(name, phone || '', email || '', role || 'cleaner', notes || '').run();

  const worker = await env.DB.prepare('SELECT * FROM workers WHERE name = ? ORDER BY id DESC LIMIT 1').bind(name).first();

  // Auto-generate codes on ALL active locks
  const locks = await env.DB.prepare("SELECT * FROM smart_locks WHERE status != 'removed'").all();
  const codes = [];

  for (const lock of locks.results) {
    try {
      const code = generateCode(6);
      const effectiveTime = new Date().toISOString();
      const codeName = `Worker: ${name} (${role || 'cleaner'})`;

      const tuyaResult = await tuyaCreateTempPassword(lock.tuya_device_id, env, {
        name: codeName, code, effectiveTime, expiryTime: null,
      });

      if (tuyaResult.success) {
        await env.DB.prepare(
          'INSERT INTO access_codes (lock_id, tuya_password_id, code, name, code_type, holder_id, holder_name, holder_phone, effective_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ).bind(
          lock.id, tuyaResult.result?.pwd_id || '', code, codeName, 'worker',
          worker.id, name, phone || '', effectiveTime
        ).run();

        codes.push({ lock_id: lock.id, lock_name: lock.name, code });

        // Set first code as worker's reference
        if (!worker.code_id) {
          const codeRecord = await env.DB.prepare('SELECT id FROM access_codes WHERE lock_id = ? AND holder_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1').bind(lock.id, worker.id).first();
          if (codeRecord) {
            await env.DB.prepare('UPDATE workers SET code_id = ? WHERE id = ?').bind(codeRecord.id, worker.id).run();
            worker.code_id = codeRecord.id;
          }
        }
      } else {
        log('warn', 'Failed to create worker code on lock', { lock: lock.name, worker: name, msg: tuyaResult.msg });
      }
    } catch (e) {
      log('error', 'Worker code creation error', { lock: lock.name, worker: name, error: e.message });
    }
  }

  ctx.waitUntil(
    ingestToBrain(env, `RAH LOCKS: Worker registered — ${name} (${role || 'cleaner'}), codes on ${codes.length} lock(s)`, 7, ['locks', 'worker-register'])
  );

  log('info', 'Worker registered', { name, role: role || 'cleaner', codes_created: codes.length });
  return json({ worker, codes }, 201);
}

// DELETE /workers/:id — Deregister worker + revoke all their codes
async function handleDeregisterWorker(path, env, ctx) {
  const workerId = parseInt(path.split('/')[2]);
  const worker = await env.DB.prepare('SELECT * FROM workers WHERE id = ?').bind(workerId).first();
  if (!worker) return err('Worker not found', 404);

  // Revoke all active codes for this worker across all locks
  const activeCodes = await env.DB.prepare(
    "SELECT ac.*, sl.tuya_device_id FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.holder_id = ? AND ac.code_type = 'worker' AND ac.is_active = 1"
  ).bind(workerId).all();

  let revoked = 0;
  for (const code of activeCodes.results) {
    try {
      if (code.tuya_password_id) {
        await tuyaDeletePassword(code.tuya_device_id, code.tuya_password_id, env).catch(() => {});
      }
      await env.DB.prepare("UPDATE access_codes SET is_active = 0, revoked_at = datetime('now'), revoke_reason = 'worker_deregistered' WHERE id = ?").bind(code.id).run();
      revoked++;
    } catch (e) {
      log('warn', 'Failed to revoke worker code', { code_id: code.id, error: e.message });
    }
  }

  // Mark worker inactive (soft delete)
  await env.DB.prepare("UPDATE workers SET is_active = 0, code_id = NULL WHERE id = ?").bind(workerId).run();

  ctx.waitUntil(
    ingestToBrain(env, `RAH LOCKS: Worker deregistered — ${worker.name} (${worker.role}), ${revoked} code(s) revoked`, 7, ['locks', 'worker-deregister'])
  );

  log('info', 'Worker deregistered', { name: worker.name, codes_revoked: revoked });
  return json({ success: true, message: `Worker "${worker.name}" deregistered`, codes_revoked: revoked });
}

// ═══════════════════════════════════════════════════════════════
// GUEST CODE LOOKUP (for Concierge AI)
// ═══════════════════════════════════════════════════════════════

async function getGuestLockCode(bookingId, env) {
  const codes = await env.DB.prepare(
    "SELECT ac.code, ac.effective_time, ac.expiry_time, sl.name as lock_name FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.booking_id = ? AND ac.code_type = 'guest' AND ac.is_active = 1"
  ).bind(bookingId).all();
  return codes.results;
}

// GET /guest/lock-codes — Authenticated guest sees their own active lock codes
async function handleGuestLockCodes(user, env) {
  // Find guest record
  const guest = await env.DB.prepare('SELECT id FROM guests WHERE email = ? OR firebase_uid = ?')
    .bind(user.email, user.uid).first();
  if (!guest) return json([]);

  // Find their active bookings
  const bookings = await env.DB.prepare(
    "SELECT id, check_in, check_out FROM bookings WHERE guest_id = ? AND status NOT IN ('cancelled', 'completed') ORDER BY check_in"
  ).bind(guest.id).all();

  if (!bookings.results.length) return json([]);

  // Get lock codes for all active bookings
  const allCodes = [];
  for (const booking of bookings.results) {
    const codes = await getGuestLockCode(booking.id, env);
    for (const c of codes) {
      allCodes.push({ ...c, check_in: booking.check_in, check_out: booking.check_out, booking_id: booking.id });
    }
  }
  return json(allCodes);
}

// ═══════════════════════════════════════════════════════════════
// WORKER CHAT — Workers can ask AI for their lock code
// ═══════════════════════════════════════════════════════════════

async function handleWorkerChat(request, user, env) {
  const body = await request.json();
  const userMessages = (body.messages || []).filter(m => m.role === 'user');
  const lastMsg = userMessages.length > 0 ? userMessages[userMessages.length - 1].content : '';
  if (!lastMsg) return json({ choices: [{ message: { content: "Hi! How can I help?" } }] });

  // Look up worker by email
  const worker = await env.DB.prepare('SELECT * FROM workers WHERE email = ? AND is_active = 1').bind(user.email).first();

  // Check if they're asking about their code
  const askingForCode = /code|door|lock|access|forgot|password|get in|open|entry/i.test(lastMsg);

  let codeContext = '';
  if (worker) {
    // Get all active codes for this worker
    const codes = await env.DB.prepare(
      "SELECT ac.code, sl.name as lock_name FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.holder_id = ? AND ac.code_type = 'worker' AND ac.is_active = 1"
    ).bind(worker.id).all();

    if (codes.results.length > 0 && askingForCode) {
      const codeList = codes.results.map(c => `${c.lock_name}: ${c.code}`).join(', ');
      codeContext = `\n\nIMPORTANT — This worker (${worker.name}, ${worker.role}) is asking about their door code. Their active code(s): ${codeList}. Give them their code directly and remind them to keep it private.`;
    } else if (codes.results.length > 0) {
      codeContext = `\n\nContext: This is ${worker.name} (${worker.role}). They have active door codes. If they ask for their code, you can provide it.`;
    } else {
      codeContext = `\n\nContext: This is ${worker.name} (${worker.role}) but they have NO active door codes. Tell them to contact the property owner to get a code assigned.`;
    }
  } else {
    codeContext = `\n\nThis user (${user.email}) is not registered as a worker. If they need access, tell them to contact the property owner.`;
  }

  const workerSystemPrompt = `You are the AI assistant for Right at Home BnB workers (cleaners, maintenance staff) in Midland, Texas.

Your role: Help workers with their lock codes, schedules, and property questions. Be friendly but brief.

If a worker asks for their door code and you have it in context, give it to them right away. Remind them to keep it private and not share it with anyone.

If they don't have a code, tell them to contact the property owner.${codeContext}`;

  const enrichedMessage = `${workerSystemPrompt}\n\n${lastMsg}`;

  try {
    const resp = await env.ECHO_CHAT.fetch('https://chat/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Echo-API-Key': env.ECHO_API_KEY || '' },
      body: JSON.stringify({
        message: enrichedMessage,
        user_id: `worker_${user.uid}`,
        site_id: 'rah-midland',
        personality: 'belle',
        max_tokens: 300,
      }),
    });
    const data = await resp.json();
    return json(data);
  } catch (e) {
    // Fallback — if echo-chat is down, at least give them their code directly
    if (worker && askingForCode) {
      const codes = await env.DB.prepare(
        "SELECT ac.code, sl.name as lock_name FROM access_codes ac JOIN smart_locks sl ON ac.lock_id = sl.id WHERE ac.holder_id = ? AND ac.code_type = 'worker' AND ac.is_active = 1"
      ).bind(worker.id).all();
      if (codes.results.length > 0) {
        const codeList = codes.results.map(c => `${c.lock_name}: ${c.code}`).join('\n');
        return json({ choices: [{ message: { content: `Here are your door codes:\n\n${codeList}\n\nPlease keep these private!` } }] });
      }
    }
    return json({ choices: [{ message: { content: "I'm having trouble right now. Please try again in a moment or contact the property owner directly." } }] });
  }
}

// ═══════════════════════════════════════════════════════════════
// ASSET TREE — Tuya SaaS Industry Pairing
// Maps RAH properties → rooms/areas → devices in Tuya hierarchy
// ═══════════════════════════════════════════════════════════════

// Ensure asset_tree table exists
async function ensureAssetTreeTable(env) {
  await env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS asset_tree (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      tuya_asset_id TEXT UNIQUE,
      parent_id INTEGER REFERENCES asset_tree(id) ON DELETE SET NULL,
      parent_tuya_asset_id TEXT,
      name TEXT NOT NULL,
      asset_type TEXT NOT NULL DEFAULT 'area',
      property_id INTEGER,
      tuya_device_id TEXT,
      metadata TEXT DEFAULT '{}',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    )
  `).run();
  await env.DB.prepare('CREATE INDEX IF NOT EXISTS idx_asset_parent ON asset_tree(parent_id)').run();
  await env.DB.prepare('CREATE INDEX IF NOT EXISTS idx_asset_tuya ON asset_tree(tuya_asset_id)').run();
  await env.DB.prepare('CREATE INDEX IF NOT EXISTS idx_asset_property ON asset_tree(property_id)').run();
  await env.DB.prepare('CREATE INDEX IF NOT EXISTS idx_asset_device ON asset_tree(tuya_device_id)').run();
}

// GET /assets — List asset tree (flat or hierarchical)
async function handleListAssets(url, env) {
  await ensureAssetTreeTable(env);
  const flat = url.searchParams.get('flat') === 'true';
  const propertyId = url.searchParams.get('property_id');

  let query = 'SELECT * FROM asset_tree';
  const params = [];
  if (propertyId) {
    query += ' WHERE property_id = ?';
    params.push(parseInt(propertyId));
  }
  query += ' ORDER BY parent_id NULLS FIRST, name';

  const stmt = params.length ? env.DB.prepare(query).bind(...params) : env.DB.prepare(query);
  const result = await stmt.all();
  const nodes = result.results;

  if (flat) return json(nodes);

  // Build hierarchical tree
  const tree = buildTree(nodes);
  return json({ tree, total: nodes.length });
}

function buildTree(nodes) {
  const map = new Map();
  const roots = [];
  for (const node of nodes) {
    map.set(node.id, { ...node, children: [] });
  }
  for (const node of nodes) {
    const treeNode = map.get(node.id);
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id).children.push(treeNode);
    } else {
      roots.push(treeNode);
    }
  }
  return roots;
}

// POST /assets — Create an asset node (Tuya + local D1)
async function handleCreateAsset(request, env, ctx) {
  await ensureAssetTreeTable(env);
  const body = await request.json();
  const { name, parent_id, asset_type, property_id, tuya_device_id, metadata } = body;
  if (!name) return err('name required');

  const validTypes = ['organization', 'property', 'building', 'floor', 'room', 'area', 'device'];
  const type = validTypes.includes(asset_type) ? asset_type : 'area';

  // Resolve parent Tuya asset ID if parent_id provided
  let parentTuyaAssetId = null;
  if (parent_id) {
    const parent = await env.DB.prepare('SELECT tuya_asset_id FROM asset_tree WHERE id = ?').bind(parent_id).first();
    if (!parent) return err('Parent asset not found', 404);
    parentTuyaAssetId = parent.tuya_asset_id;
  }

  // Create in Tuya
  let tuyaAssetId = null;
  const tuyaResult = await tuyaCreateAsset(name, parentTuyaAssetId, env);
  if (tuyaResult.success && tuyaResult.result) {
    tuyaAssetId = tuyaResult.result.asset_id || tuyaResult.result;
  } else {
    log('warn', 'Tuya asset creation failed, storing locally only', { msg: tuyaResult.msg });
  }

  // Store in D1
  await env.DB.prepare(`
    INSERT INTO asset_tree (tuya_asset_id, parent_id, parent_tuya_asset_id, name, asset_type, property_id, tuya_device_id, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    tuyaAssetId || `local_${Date.now()}`,
    parent_id || null,
    parentTuyaAssetId,
    name,
    type,
    property_id || null,
    tuya_device_id || null,
    JSON.stringify(metadata || {})
  ).run();

  const asset = await env.DB.prepare('SELECT * FROM asset_tree WHERE name = ? ORDER BY id DESC LIMIT 1').bind(name).first();

  // If this is a device node and tuya_device_id provided, assign in Tuya
  if (type === 'device' && tuya_device_id && tuyaAssetId) {
    ctx.waitUntil(
      tuyaAssignDeviceToAsset(tuyaAssetId, tuya_device_id, env)
        .then(r => { if (!r.success) log('warn', 'Tuya device assignment failed', { msg: r.msg }); })
        .catch(e => log('warn', 'Tuya device assignment error', { error: e.message }))
    );
  }

  ctx.waitUntil(
    ingestToBrain(env, `RAH ASSETS: Created asset "${name}" (${type})${parent_id ? ` under parent #${parent_id}` : ' at root'}`, 6, ['assets', 'create'])
  );

  log('info', 'Asset created', { name, type, tuya_asset_id: tuyaAssetId });
  return json(asset, 201);
}

// GET /assets/:id — Get single asset with children + devices
async function handleGetAsset(path, env) {
  await ensureAssetTreeTable(env);
  const assetId = parseInt(path.split('/')[2]);
  const asset = await env.DB.prepare('SELECT * FROM asset_tree WHERE id = ?').bind(assetId).first();
  if (!asset) return err('Asset not found', 404);

  const [children, devices] = await Promise.all([
    env.DB.prepare('SELECT * FROM asset_tree WHERE parent_id = ? ORDER BY name').bind(assetId).all(),
    env.DB.prepare("SELECT * FROM asset_tree WHERE parent_id = ? AND asset_type = 'device' ORDER BY name").bind(assetId).all(),
  ]);

  // If Tuya asset ID exists, try to get live status from Tuya
  let tuyaInfo = null;
  if (asset.tuya_asset_id && !asset.tuya_asset_id.startsWith('local_')) {
    const tuyaResult = await tuyaGetAsset(asset.tuya_asset_id, env);
    if (tuyaResult.success) tuyaInfo = tuyaResult.result;
  }

  // If it's a device node, get lock info
  let lockInfo = null;
  if (asset.tuya_device_id) {
    lockInfo = await env.DB.prepare('SELECT * FROM smart_locks WHERE tuya_device_id = ?').bind(asset.tuya_device_id).first();
  }

  return json({
    ...asset,
    children: children.results,
    device_nodes: devices.results,
    tuya_info: tuyaInfo,
    lock_info: lockInfo,
  });
}

// PUT /assets/:id — Update asset name/metadata
async function handleUpdateAsset(request, path, env, ctx) {
  await ensureAssetTreeTable(env);
  const assetId = parseInt(path.split('/')[2]);
  const asset = await env.DB.prepare('SELECT * FROM asset_tree WHERE id = ?').bind(assetId).first();
  if (!asset) return err('Asset not found', 404);

  const body = await request.json();
  const fields = [];
  const values = [];

  if (body.name !== undefined) {
    fields.push('name = ?');
    values.push(body.name);
    // Update in Tuya too
    if (asset.tuya_asset_id && !asset.tuya_asset_id.startsWith('local_')) {
      ctx.waitUntil(
        tuyaUpdateAsset(asset.tuya_asset_id, body.name, env)
          .catch(e => log('warn', 'Tuya asset update failed', { error: e.message }))
      );
    }
  }
  if (body.asset_type !== undefined) { fields.push('asset_type = ?'); values.push(body.asset_type); }
  if (body.property_id !== undefined) { fields.push('property_id = ?'); values.push(body.property_id); }
  if (body.metadata !== undefined) { fields.push('metadata = ?'); values.push(JSON.stringify(body.metadata)); }

  if (fields.length === 0) return err('No valid fields to update');

  fields.push("updated_at = datetime('now')");
  values.push(assetId);

  await env.DB.prepare(`UPDATE asset_tree SET ${fields.join(', ')} WHERE id = ?`).bind(...values).run();
  const updated = await env.DB.prepare('SELECT * FROM asset_tree WHERE id = ?').bind(assetId).first();

  log('info', 'Asset updated', { id: assetId, name: updated.name });
  return json(updated);
}

// DELETE /assets/:id — Delete asset node (Tuya + local)
async function handleDeleteAssetNode(path, env, ctx) {
  await ensureAssetTreeTable(env);
  const assetId = parseInt(path.split('/')[2]);
  const asset = await env.DB.prepare('SELECT * FROM asset_tree WHERE id = ?').bind(assetId).first();
  if (!asset) return err('Asset not found', 404);

  // Check for children — refuse if has children (must delete bottom-up)
  const children = await env.DB.prepare('SELECT COUNT(*) as count FROM asset_tree WHERE parent_id = ?').bind(assetId).first();
  if (children.count > 0) {
    return err(`Cannot delete asset with ${children.count} child nodes. Delete children first.`, 409);
  }

  // Delete from Tuya
  if (asset.tuya_asset_id && !asset.tuya_asset_id.startsWith('local_')) {
    ctx.waitUntil(
      tuyaDeleteAsset(asset.tuya_asset_id, env)
        .catch(e => log('warn', 'Tuya asset delete failed', { error: e.message }))
    );
  }

  await env.DB.prepare('DELETE FROM asset_tree WHERE id = ?').bind(assetId).run();

  ctx.waitUntil(
    ingestToBrain(env, `RAH ASSETS: Deleted asset "${asset.name}" (${asset.asset_type})`, 6, ['assets', 'delete'])
  );

  log('info', 'Asset deleted', { id: assetId, name: asset.name });
  return json({ success: true, message: `Asset "${asset.name}" deleted` });
}

// GET /assets/:id/children — List child assets
async function handleGetAssetChildren(path, env) {
  await ensureAssetTreeTable(env);
  const assetId = parseInt(path.split('/')[2]);
  const asset = await env.DB.prepare('SELECT id FROM asset_tree WHERE id = ?').bind(assetId).first();
  if (!asset) return err('Asset not found', 404);

  const children = await env.DB.prepare('SELECT * FROM asset_tree WHERE parent_id = ? ORDER BY asset_type, name').bind(assetId).all();
  return json(children.results);
}

// GET /assets/:id/devices — List devices under this asset (local + Tuya)
async function handleGetAssetDevices(path, env) {
  await ensureAssetTreeTable(env);
  const assetId = parseInt(path.split('/')[2]);
  const asset = await env.DB.prepare('SELECT * FROM asset_tree WHERE id = ?').bind(assetId).first();
  if (!asset) return err('Asset not found', 404);

  // Local device nodes under this asset
  const localDevices = await env.DB.prepare(
    "SELECT at.*, sl.name as lock_name, sl.status as lock_status, sl.model as lock_model FROM asset_tree at LEFT JOIN smart_locks sl ON at.tuya_device_id = sl.tuya_device_id WHERE at.parent_id = ? AND at.asset_type = 'device' ORDER BY at.name"
  ).bind(assetId).all();

  // Also try Tuya API for live device list
  let tuyaDevices = [];
  if (asset.tuya_asset_id && !asset.tuya_asset_id.startsWith('local_')) {
    const tuyaResult = await tuyaGetAssetDevices(asset.tuya_asset_id, env);
    if (tuyaResult.success && tuyaResult.result) {
      tuyaDevices = tuyaResult.result.list || tuyaResult.result || [];
    }
  }

  return json({ local_devices: localDevices.results, tuya_devices: tuyaDevices });
}

// POST /assets/:id/devices — Assign a Tuya device to an asset node
async function handleAssignDevice(request, path, env, ctx) {
  await ensureAssetTreeTable(env);
  const assetId = parseInt(path.split('/')[2]);
  const asset = await env.DB.prepare('SELECT * FROM asset_tree WHERE id = ?').bind(assetId).first();
  if (!asset) return err('Asset not found', 404);

  const body = await request.json();
  const { tuya_device_id, name } = body;
  if (!tuya_device_id) return err('tuya_device_id required');

  // Verify device exists
  const deviceInfo = await tuyaGetDevice(tuya_device_id, env);
  if (!deviceInfo.success) {
    return err(`Device not found on Tuya: ${deviceInfo.msg || 'unknown error'}`, 404);
  }

  const deviceName = name || deviceInfo.result?.name || `Device ${tuya_device_id.slice(-6)}`;

  // Assign in Tuya if asset has a Tuya ID
  if (asset.tuya_asset_id && !asset.tuya_asset_id.startsWith('local_')) {
    const assignResult = await tuyaAssignDeviceToAsset(asset.tuya_asset_id, tuya_device_id, env);
    if (!assignResult.success) {
      log('warn', 'Tuya device assignment failed', { msg: assignResult.msg });
    }
  }

  // Create device node in local asset tree
  await env.DB.prepare(`
    INSERT INTO asset_tree (tuya_asset_id, parent_id, parent_tuya_asset_id, name, asset_type, property_id, tuya_device_id, metadata)
    VALUES (?, ?, ?, ?, 'device', ?, ?, ?)
  `).bind(
    `dev_${tuya_device_id}`,
    assetId,
    asset.tuya_asset_id,
    deviceName,
    asset.property_id,
    tuya_device_id,
    JSON.stringify({
      product_name: deviceInfo.result?.product_name || '',
      online: deviceInfo.result?.online || false,
      category: deviceInfo.result?.category || '',
    })
  ).run();

  const deviceNode = await env.DB.prepare('SELECT * FROM asset_tree WHERE tuya_device_id = ? ORDER BY id DESC LIMIT 1').bind(tuya_device_id).first();

  ctx.waitUntil(
    ingestToBrain(env, `RAH ASSETS: Device "${deviceName}" assigned to asset "${asset.name}"`, 6, ['assets', 'device-assign'])
  );

  log('info', 'Device assigned to asset', { device: deviceName, asset: asset.name });
  return json(deviceNode, 201);
}

// DELETE /assets/:id/devices/:deviceId — Remove device from asset
async function handleRemoveDevice(path, env, ctx) {
  await ensureAssetTreeTable(env);
  const parts = path.split('/');
  const assetId = parseInt(parts[2]);
  const tuyaDeviceId = parts[4];

  const asset = await env.DB.prepare('SELECT * FROM asset_tree WHERE id = ?').bind(assetId).first();
  if (!asset) return err('Asset not found', 404);

  // Remove from Tuya
  if (asset.tuya_asset_id && !asset.tuya_asset_id.startsWith('local_')) {
    ctx.waitUntil(
      tuyaRemoveDeviceFromAsset(asset.tuya_asset_id, tuyaDeviceId, env)
        .catch(e => log('warn', 'Tuya device removal failed', { error: e.message }))
    );
  }

  // Remove device node from local tree
  const deleted = await env.DB.prepare('DELETE FROM asset_tree WHERE parent_id = ? AND tuya_device_id = ?').bind(assetId, tuyaDeviceId).run();

  log('info', 'Device removed from asset', { asset: asset.name, device: tuyaDeviceId });
  return json({ success: true, rows_deleted: deleted.meta.changes });
}

// POST /assets/sync — Pull asset tree from Tuya and merge into local D1
async function handleSyncAssets(env, ctx) {
  await ensureAssetTreeTable(env);

  // Get top-level assets from Tuya
  const topResult = await tuyaListAssets(env);
  if (!topResult.success) {
    return err(`Tuya API error: ${topResult.msg || 'Failed to list assets'}`, 502);
  }

  const assets = topResult.result?.list || topResult.result || [];
  let synced = 0;
  let created = 0;

  // Recursive function to sync an asset and its children
  async function syncAssetNode(tuyaAsset, parentId, depth = 0) {
    if (depth > 5) return; // Safety limit

    const tuyaId = tuyaAsset.asset_id || tuyaAsset.id;
    const name = tuyaAsset.asset_name || tuyaAsset.name || `Asset ${tuyaId}`;

    // Check if already in D1
    let local = await env.DB.prepare('SELECT id FROM asset_tree WHERE tuya_asset_id = ?').bind(String(tuyaId)).first();
    if (!local) {
      await env.DB.prepare(`
        INSERT INTO asset_tree (tuya_asset_id, parent_id, parent_tuya_asset_id, name, asset_type, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
      `).bind(
        String(tuyaId),
        parentId,
        parentId ? (await env.DB.prepare('SELECT tuya_asset_id FROM asset_tree WHERE id = ?').bind(parentId).first())?.tuya_asset_id : null,
        name,
        depth === 0 ? 'organization' : (depth === 1 ? 'property' : (depth === 2 ? 'room' : 'area')),
        JSON.stringify({ synced_from_tuya: true, tuya_type: tuyaAsset.asset_type || '' })
      ).run();
      local = await env.DB.prepare('SELECT id FROM asset_tree WHERE tuya_asset_id = ?').bind(String(tuyaId)).first();
      created++;
    } else {
      // Update name in case it changed
      await env.DB.prepare("UPDATE asset_tree SET name = ?, updated_at = datetime('now') WHERE id = ?").bind(name, local.id).run();
    }
    synced++;

    // Get children
    const childResult = await tuyaGetSubAssets(String(tuyaId), env);
    if (childResult.success) {
      const children = childResult.result?.list || childResult.result || [];
      for (const child of children) {
        await syncAssetNode(child, local.id, depth + 1);
      }
    }

    // Get devices at this level
    const deviceResult = await tuyaGetAssetDevices(String(tuyaId), env);
    if (deviceResult.success) {
      const devices = deviceResult.result?.list || deviceResult.result || [];
      for (const device of devices) {
        const devId = device.device_id || device.id;
        const devName = device.name || `Device ${devId?.slice(-6) || 'unknown'}`;
        const existing = await env.DB.prepare('SELECT id FROM asset_tree WHERE tuya_device_id = ? AND parent_id = ?').bind(devId, local.id).first();
        if (!existing && devId) {
          await env.DB.prepare(`
            INSERT INTO asset_tree (tuya_asset_id, parent_id, parent_tuya_asset_id, name, asset_type, tuya_device_id, metadata)
            VALUES (?, ?, ?, ?, 'device', ?, ?)
          `).bind(
            `dev_${devId}`, local.id, String(tuyaId), devName, devId,
            JSON.stringify({ product_name: device.product_name || '', category: device.category || '', online: device.online || false })
          ).run();
          created++;
        }
        synced++;
      }
    }
  }

  for (const asset of assets) {
    await syncAssetNode(asset, null, 0);
  }

  ctx.waitUntil(
    ingestToBrain(env, `RAH ASSETS: Synced from Tuya — ${synced} nodes processed, ${created} new`, 7, ['assets', 'sync'])
  );

  log('info', 'Asset sync complete', { synced, created });
  return json({ success: true, synced, created, tuya_top_level: assets.length });
}

// POST /assets/initialize — Bootstrap asset tree from existing properties + locks
// Creates: Organization → Property → Areas (based on lock locations) → Device nodes
async function handleInitializeAssetTree(env, ctx) {
  await ensureAssetTreeTable(env);

  // Check if tree already has nodes
  const existing = await env.DB.prepare('SELECT COUNT(*) as count FROM asset_tree').first();
  if (existing.count > 0) {
    return err(`Asset tree already has ${existing.count} nodes. Use /assets/sync to update, or delete existing nodes first.`, 409);
  }

  // 1. Create organization root
  const orgName = env.PROPERTY_NAME || 'Right at Home BnB';
  const orgResult = await tuyaCreateAsset(orgName, null, env);
  const orgTuyaId = (orgResult.success && orgResult.result) ? (orgResult.result.asset_id || orgResult.result) : `local_org_${Date.now()}`;

  await env.DB.prepare(`
    INSERT INTO asset_tree (tuya_asset_id, name, asset_type, metadata)
    VALUES (?, ?, 'organization', ?)
  `).bind(orgTuyaId, orgName, JSON.stringify({ city: env.PROPERTY_CITY || 'Midland', state: env.PROPERTY_STATE || 'TX' })).run();

  const orgNode = await env.DB.prepare('SELECT * FROM asset_tree WHERE tuya_asset_id = ?').bind(orgTuyaId).first();

  // 2. Create property nodes from D1 properties table
  const properties = await env.DB.prepare('SELECT * FROM properties').all();
  const propertyNodes = [];

  for (const prop of properties.results) {
    const propResult = await tuyaCreateAsset(prop.name || `Property ${prop.id}`, orgTuyaId, env);
    const propTuyaId = (propResult.success && propResult.result) ? (propResult.result.asset_id || propResult.result) : `local_prop_${prop.id}`;

    await env.DB.prepare(`
      INSERT INTO asset_tree (tuya_asset_id, parent_id, parent_tuya_asset_id, name, asset_type, property_id, metadata)
      VALUES (?, ?, ?, ?, 'property', ?, ?)
    `).bind(propTuyaId, orgNode.id, orgTuyaId, prop.name || `Property ${prop.id}`, prop.id, JSON.stringify({ address: prop.address || '' })).run();

    const propNode = await env.DB.prepare('SELECT * FROM asset_tree WHERE tuya_asset_id = ?').bind(propTuyaId).first();
    propertyNodes.push({ propNode, prop });
  }

  // 3. Create room/area nodes + assign locks as device nodes
  const locks = await env.DB.prepare('SELECT * FROM smart_locks').all();
  let deviceNodes = 0;

  for (const lock of locks.results) {
    // Find which property this lock belongs to (use location field or first property)
    let parentNode = propertyNodes[0]?.propNode; // Default to first property
    for (const pn of propertyNodes) {
      if (lock.location && pn.prop.name && lock.location.toLowerCase().includes(pn.prop.name.toLowerCase())) {
        parentNode = pn.propNode;
        break;
      }
    }
    if (!parentNode) continue;

    // Create an area node for the lock's location
    const areaName = lock.location || lock.name || `Lock Area ${lock.id}`;
    const areaTuyaId = `local_area_lock_${lock.id}`;

    // Check if area already exists (from a previous partial init)
    let areaNode = await env.DB.prepare('SELECT * FROM asset_tree WHERE tuya_asset_id = ?').bind(areaTuyaId).first();
    if (!areaNode) {
      await env.DB.prepare(`
        INSERT INTO asset_tree (tuya_asset_id, parent_id, parent_tuya_asset_id, name, asset_type, property_id, metadata)
        VALUES (?, ?, ?, ?, 'area', ?, '{}')
      `).bind(areaTuyaId, parentNode.id, parentNode.tuya_asset_id, areaName, parentNode.property_id).run();
      areaNode = await env.DB.prepare('SELECT * FROM asset_tree WHERE tuya_asset_id = ?').bind(areaTuyaId).first();
    }

    // Create device node for the lock
    await env.DB.prepare(`
      INSERT INTO asset_tree (tuya_asset_id, parent_id, parent_tuya_asset_id, name, asset_type, property_id, tuya_device_id, metadata)
      VALUES (?, ?, ?, ?, 'device', ?, ?, ?)
    `).bind(
      `dev_${lock.tuya_device_id}`,
      areaNode.id,
      areaNode.tuya_asset_id,
      lock.name || `Lock ${lock.id}`,
      parentNode.property_id,
      lock.tuya_device_id,
      JSON.stringify({ model: lock.model || 'Arpha D280W', status: lock.status })
    ).run();
    deviceNodes++;

    // Assign to Tuya asset if the area has a real Tuya ID
    if (parentNode.tuya_asset_id && !parentNode.tuya_asset_id.startsWith('local_')) {
      ctx.waitUntil(
        tuyaAssignDeviceToAsset(parentNode.tuya_asset_id, lock.tuya_device_id, env)
          .catch(e => log('warn', 'Tuya device assignment during init failed', { error: e.message }))
      );
    }
  }

  const totalNodes = await env.DB.prepare('SELECT COUNT(*) as count FROM asset_tree').first();

  ctx.waitUntil(
    ingestToBrain(env, `RAH ASSETS: Initialized asset tree — ${totalNodes.count} nodes (1 org, ${propertyNodes.length} properties, ${deviceNodes} devices)`, 8, ['assets', 'initialize'])
  );

  log('info', 'Asset tree initialized', { total: totalNodes.count, properties: propertyNodes.length, devices: deviceNodes });
  return json({
    success: true,
    message: 'Asset tree initialized',
    total_nodes: totalNodes.count,
    organization: orgNode,
    properties: propertyNodes.length,
    device_nodes: deviceNodes,
  }, 201);
}

// ═══════════════════════════════════════════════════════════════
// ANALYTICS
// ═══════════════════════════════════════════════════════════════

async function handleAnalytics(url, env) {
  const range = url.searchParams.get('range') || '30d';
  const daysMap = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 };
  const days = daysMap[range] || 30;

  const now = new Date();
  const periodStart = new Date(now.getTime() - days * 86400000).toISOString().split('T')[0];
  const prevStart = new Date(now.getTime() - days * 2 * 86400000).toISOString().split('T')[0];
  const today = now.toISOString().split('T')[0];
  const yearAgo = new Date(now.getTime() - 365 * 86400000).toISOString().split('T')[0];

  const [
    curRevResult, prevRevResult,
    curBookResult, prevBookResult,
    curExpResult, prevExpResult,
    monthlyRev, monthlyBook, monthlyNights,
    reviewSources, propResult, ratingResult,
  ] = await Promise.all([
    // Current period revenue (paid invoices)
    env.DB.prepare(
      "SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE status = 'paid' AND issue_date >= ?"
    ).bind(periodStart).first(),
    // Previous period revenue
    env.DB.prepare(
      "SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE status = 'paid' AND issue_date >= ? AND issue_date < ?"
    ).bind(prevStart, periodStart).first(),
    // Current period bookings
    env.DB.prepare(
      "SELECT COUNT(*) as total FROM bookings WHERE status != 'cancelled' AND check_in >= ?"
    ).bind(periodStart).first(),
    // Previous period bookings
    env.DB.prepare(
      "SELECT COUNT(*) as total FROM bookings WHERE status != 'cancelled' AND check_in >= ? AND check_in < ?"
    ).bind(prevStart, periodStart).first(),
    // Current period expenses
    env.DB.prepare(
      "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ?"
    ).bind(periodStart).first(),
    // Previous period expenses
    env.DB.prepare(
      "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ? AND date < ?"
    ).bind(prevStart, periodStart).first(),
    // Monthly revenue (last 12 months)
    env.DB.prepare(
      "SELECT strftime('%Y-%m', issue_date) as month, COALESCE(SUM(total), 0) as revenue FROM invoices WHERE status = 'paid' AND issue_date >= ? GROUP BY month ORDER BY month"
    ).bind(yearAgo).all(),
    // Monthly bookings (last 12 months)
    env.DB.prepare(
      "SELECT strftime('%Y-%m', check_in) as month, COUNT(*) as bookings FROM bookings WHERE status != 'cancelled' AND check_in >= ? GROUP BY month ORDER BY month"
    ).bind(yearAgo).all(),
    // Monthly booked nights (last 12 months) for occupancy
    env.DB.prepare(
      "SELECT strftime('%Y-%m', check_in) as month, SUM(CAST(julianday(check_out) - julianday(check_in) AS INTEGER)) as nights FROM bookings WHERE status != 'cancelled' AND check_in >= ? GROUP BY month ORDER BY month"
    ).bind(yearAgo).all(),
    // Booking platform distribution from review sources
    env.DB.prepare(
      "SELECT source, COUNT(*) as count FROM reviews GROUP BY source ORDER BY count DESC"
    ).all(),
    // Property stats
    env.DB.prepare(`
      SELECT p.id, p.name, p.nightly_rate,
        (SELECT COALESCE(SUM(i.total), 0) FROM invoices i WHERE i.status = 'paid' AND i.guest_email IN (SELECT g.email FROM guests g JOIN bookings b ON b.guest_id = g.id WHERE b.room_name = p.name)) as revenue,
        (SELECT COUNT(*) FROM bookings b WHERE b.room_name = p.name AND b.status != 'cancelled') as bookings,
        (SELECT COALESCE(SUM(CAST(julianday(b.check_out) - julianday(b.check_in) AS INTEGER)), 0) FROM bookings b WHERE b.room_name = p.name AND b.status != 'cancelled' AND b.check_in >= ?) as booked_nights
      FROM properties p ORDER BY p.id
    `).bind(yearAgo).all(),
    // Average rating
    env.DB.prepare("SELECT AVG(rating) as avg, COUNT(*) as count FROM reviews").first(),
  ]);

  // Build monthly chart data (last 12 months)
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const revMap = {};
  for (const r of (monthlyRev.results || [])) revMap[r.month] = r.revenue;
  const bookMap = {};
  for (const r of (monthlyBook.results || [])) bookMap[r.month] = r.bookings;
  const nightsMap = {};
  for (const r of (monthlyNights.results || [])) nightsMap[r.month] = r.nights;

  const propCount = (propResult.results || []).length || 1;
  const monthly = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const daysInMonth = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
    const totalAvailNights = daysInMonth * propCount;
    const bookedNights = nightsMap[key] || 0;
    monthly.push({
      month: monthNames[d.getMonth()],
      revenue: revMap[key] || 0,
      bookings: bookMap[key] || 0,
      occupancy: totalAvailNights > 0 ? Math.round((bookedNights / totalAvailNights) * 100) : 0,
    });
  }

  // Totals with % change
  const curRev = curRevResult.total || 0;
  const prevRev = prevRevResult.total || 0;
  const curBook = curBookResult.total || 0;
  const prevBook = prevBookResult.total || 0;
  const curExp = curExpResult.total || 0;
  const prevExp = prevExpResult.total || 0;

  function pctChange(cur, prev) {
    if (prev === 0) return cur > 0 ? 100 : 0;
    return ((cur - prev) / prev) * 100;
  }

  // Avg nightly rate from bookings in period
  const avgRate = curBook > 0 ? curRev / Math.max(curBook, 1) : (propResult.results || []).reduce((s, p) => s + (p.nightly_rate || 85), 0) / propCount;

  // Occupancy for period
  const periodNights = (monthlyNights.results || []).reduce((s, r) => s + (r.nights || 0), 0);
  const periodDays = days * propCount;
  const avgOccupancy = periodDays > 0 ? Math.round((periodNights / periodDays) * 100) : 0;

  // Platform distribution
  const platformColors = {
    airbnb: '#FF5A5F', vrbo: '#3D5A80', direct: '#10B981',
    'booking.com': '#003580', google: '#4285F4', other: '#6B7280',
  };
  const sources = (reviewSources.results || []);
  const totalReviews = sources.reduce((s, r) => s + r.count, 0) || 1;
  const platforms = sources.map(s => ({
    name: s.source.charAt(0).toUpperCase() + s.source.slice(1),
    value: Math.round((s.count / totalReviews) * 100),
    color: platformColors[s.source.toLowerCase()] || platformColors.other,
  }));
  if (platforms.length === 0) {
    platforms.push({ name: 'Direct', value: 100, color: platformColors.direct });
  }

  // Property performance
  const properties = (propResult.results || []).map(p => ({
    id: String(p.id),
    name: p.name,
    revenue: p.revenue || 0,
    bookings: p.bookings || 0,
    occupancy: p.booked_nights > 0 ? Math.min(Math.round((p.booked_nights / 365) * 100), 100) : 0,
    avgNightlyRate: p.nightly_rate || 85,
    avgRating: ratingResult.avg ? parseFloat(ratingResult.avg).toFixed(1) : '5.0',
  }));

  return json({
    totals: {
      totalRevenue: curRev,
      revenueChange: parseFloat(pctChange(curRev, prevRev).toFixed(1)),
      totalBookings: curBook,
      bookingsChange: parseFloat(pctChange(curBook, prevBook).toFixed(1)),
      avgOccupancy,
      occupancyChange: 0,
      avgNightlyRate: Math.round(avgRate),
      rateChange: 0,
      totalExpenses: curExp,
      expensesChange: parseFloat(pctChange(curExp, prevExp).toFixed(1)),
      avgRating: ratingResult.avg ? parseFloat(ratingResult.avg).toFixed(1) : '5.0',
      reviewCount: ratingResult.count || 0,
    },
    monthly,
    platforms,
    properties,
  });
}

// ═══════════════════════════════════════════════════════════════
// ADMIN COSTS (cost tracker + property profitability)
// ═══════════════════════════════════════════════════════════════

async function handleAdminCosts(url, env) {
  const month = url.searchParams.get('month'); // YYYY-MM, defaults to current month
  const now = new Date();
  const currentMonth = month || now.toISOString().slice(0, 7);
  const yearStart = now.getFullYear() + '-01-01';

  // Ensure property + recurring columns exist (idempotent migration)
  try {
    await env.DB.prepare("ALTER TABLE expenses ADD COLUMN property TEXT DEFAULT ''").run();
  } catch (_) { /* column already exists */ }
  try {
    await env.DB.prepare("ALTER TABLE expenses ADD COLUMN recurring INTEGER DEFAULT 0").run();
  } catch (_) { /* column already exists */ }

  const daysInMonth = new Date(
    parseInt(currentMonth.slice(0, 4)),
    parseInt(currentMonth.slice(5, 7)),
    0
  ).getDate();

  const [expensesResult, propertiesResult, revenueByPropResult, nightsByPropResult] = await Promise.all([
    // All expenses for the selected month
    env.DB.prepare(
      "SELECT id, category, description, amount, date, vendor, COALESCE(property, '') as property, COALESCE(recurring, 0) as recurring FROM expenses WHERE date LIKE ? ORDER BY date DESC"
    ).bind(currentMonth + '%').all(),
    // All properties
    env.DB.prepare("SELECT id, name, address, nightly_rate FROM properties ORDER BY name").all(),
    // Revenue by property for the selected month (from paid invoices)
    env.DB.prepare(`
      SELECT b.room_name, COALESCE(SUM(i.total), 0) as revenue
      FROM invoices i
      JOIN guests g ON i.guest_name = g.name
      JOIN bookings b ON b.guest_id = g.id
      WHERE i.status = 'paid' AND strftime('%Y-%m', i.issue_date) = ?
      GROUP BY b.room_name
    `).bind(currentMonth).all(),
    // Booked nights by property for the selected month
    env.DB.prepare(`
      SELECT room_name,
        COALESCE(SUM(CAST(julianday(check_out) - julianday(check_in) AS INTEGER)), 0) as nights
      FROM bookings
      WHERE status != 'cancelled' AND strftime('%Y-%m', check_in) = ?
      GROUP BY room_name
    `).bind(currentMonth).all(),
  ]);

  const properties = propertiesResult.results || [];
  const propertyNames = properties.map(p => p.name);

  // Map expenses to frontend format (amountCents)
  const expenses = (expensesResult.results || []).map(e => ({
    id: 'EXP-' + String(e.id).padStart(3, '0'),
    date: e.date,
    category: (e.category || 'Maintenance').charAt(0).toUpperCase() + (e.category || 'maintenance').slice(1),
    description: e.description,
    amountCents: Math.round((e.amount || 0) * 100),
    property: e.property || '',
    vendor: e.vendor || '',
    recurring: !!e.recurring,
  }));

  // Build revenue and nights maps
  const revByProp = {};
  for (const r of (revenueByPropResult.results || [])) revByProp[r.room_name] = r.revenue;
  const nightsByProp = {};
  for (const r of (nightsByPropResult.results || [])) nightsByProp[r.room_name] = r.nights;

  // Calculate per-property expenses (expenses with a property field go to that property; unassigned split evenly)
  const expByProp = {};
  let unassignedExp = 0;
  for (const e of (expensesResult.results || [])) {
    const amt = e.amount || 0;
    if (e.property && propertyNames.includes(e.property)) {
      expByProp[e.property] = (expByProp[e.property] || 0) + amt;
    } else {
      unassignedExp += amt;
    }
  }
  const propCount = properties.length || 1;
  const unassignedPerProp = unassignedExp / propCount;

  // Build property profits
  const propertyProfits = properties.map(p => {
    const rev = revByProp[p.name] || 0;
    const exp = (expByProp[p.name] || 0) + unassignedPerProp;
    const nights = nightsByProp[p.name] || 0;
    const avgRate = p.nightly_rate || 85;
    return {
      name: p.name,
      address: p.address || '',
      revenueCents: Math.round(rev * 100),
      expensesCents: Math.round(exp * 100),
      nightsAvailable: daysInMonth,
      nightsBooked: nights,
      avgNightlyRateCents: Math.round(avgRate * 100),
    };
  });

  return json({ month: currentMonth, expenses, properties: propertyNames, propertyProfits });
}

// ═══════════════════════════════════════════════════════════════
// ADMIN FINANCE (full financial god-view)
// ═══════════════════════════════════════════════════════════════

async function handleAdminFinance(url, env) {
  const range = url.searchParams.get('range') || 'mtd';
  const now = new Date();
  const yearStart = now.getFullYear() + '-01-01';
  const monthStart = now.toISOString().slice(0, 7) + '-01';
  const qtrMonth = Math.floor(now.getMonth() / 3) * 3;
  const qtrStart = `${now.getFullYear()}-${String(qtrMonth + 1).padStart(2, '0')}-01`;
  const yearAgo = new Date(now.getTime() - 365 * 86400000).toISOString().split('T')[0];
  const today = now.toISOString().split('T')[0];

  const periodStart = range === 'ytd' ? yearStart : range === 'qtd' ? qtrStart : monthStart;
  const daysInPeriod = Math.ceil((now.getTime() - new Date(periodStart).getTime()) / 86400000) || 1;

  const [
    propertiesResult, revenueByPropResult, expByPropResult,
    nightsByPropResult, monthlyRevResult, monthlyExpResult,
    expByCatResult, reviewsResult,
  ] = await Promise.all([
    // All properties
    env.DB.prepare("SELECT id, name, address, bedrooms, nightly_rate, status FROM properties ORDER BY id").all(),
    // Revenue by property (from bookings linked to invoices)
    env.DB.prepare(`
      SELECT b.room_name, COALESCE(SUM(i.total), 0) as revenue
      FROM invoices i
      JOIN guests g ON i.guest_name = g.name
      JOIN bookings b ON b.guest_id = g.id
      WHERE i.status = 'paid' AND i.issue_date >= ?
      GROUP BY b.room_name
    `).bind(periodStart).all(),
    // Expenses by property — expenses don't have property_id, use total
    env.DB.prepare(
      "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ?"
    ).bind(periodStart).first(),
    // Booked nights by property
    env.DB.prepare(`
      SELECT room_name, COALESCE(SUM(CAST(julianday(check_out) - julianday(check_in) AS INTEGER)), 0) as nights,
        COUNT(*) as bookings
      FROM bookings WHERE status != 'cancelled' AND check_in >= ?
      GROUP BY room_name
    `).bind(periodStart).all(),
    // Monthly revenue (last 12 months)
    env.DB.prepare(
      "SELECT strftime('%Y-%m', issue_date) as month, COALESCE(SUM(total), 0) as revenue FROM invoices WHERE status = 'paid' AND issue_date >= ? GROUP BY month ORDER BY month"
    ).bind(yearAgo).all(),
    // Monthly expenses (last 12 months)
    env.DB.prepare(
      "SELECT strftime('%Y-%m', date) as month, COALESCE(SUM(amount), 0) as expenses FROM expenses WHERE date >= ? GROUP BY month ORDER BY month"
    ).bind(yearAgo).all(),
    // Expense breakdown by category for period
    env.DB.prepare(
      "SELECT category, COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ? GROUP BY category ORDER BY total DESC"
    ).bind(periodStart).all(),
    // Average rating
    env.DB.prepare("SELECT AVG(rating) as avg FROM reviews").first(),
  ]);

  const properties = propertiesResult.results || [];
  const propCount = properties.length || 1;

  // Build revenue/nights maps
  const revByProp = {};
  for (const r of (revenueByPropResult.results || [])) revByProp[r.room_name] = r.revenue;
  const nightsByProp = {};
  const bookingsByProp = {};
  for (const r of (nightsByPropResult.results || [])) {
    nightsByProp[r.room_name] = r.nights;
    bookingsByProp[r.room_name] = r.bookings;
  }

  // Split total expenses evenly across properties (no per-property expense tracking)
  const totalExpenses = expByPropResult.total || 0;
  const expPerProp = propCount > 0 ? totalExpenses / propCount : 0;

  // Property financials
  const propertyFinancials = properties.map(p => {
    const rev = revByProp[p.name] || 0;
    const exp = expPerProp;
    const nights = nightsByProp[p.name] || 0;
    const bookings = bookingsByProp[p.name] || 0;
    const occupancy = daysInPeriod > 0 ? Math.min(Math.round((nights / daysInPeriod) * 100), 100) : 0;
    const avgDaily = bookings > 0 ? Math.round(rev / bookings) : (p.nightly_rate || 85);
    const revPAR = daysInPeriod > 0 ? Math.round(rev / daysInPeriod) : 0;
    return {
      propertyId: String(p.id),
      propertyName: p.name,
      grossRevenue: rev,
      expenses: Math.round(exp),
      netProfit: Math.round(rev - exp),
      occupancyPercent: occupancy,
      profitMarginPercent: rev > 0 ? parseFloat(((rev - exp) / rev * 100).toFixed(1)) : 0,
      totalNights: daysInPeriod,
      bookedNights: nights,
      avgDailyRate: avgDaily,
      revPAR,
    };
  });

  // Monthly chart data (last 12 months)
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const revMap = {};
  for (const r of (monthlyRevResult.results || [])) revMap[r.month] = r.revenue;
  const expMap = {};
  for (const r of (monthlyExpResult.results || [])) expMap[r.month] = r.expenses;

  const monthlyData = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const rev = revMap[key] || 0;
    const exp = expMap[key] || 0;
    monthlyData.push({
      month: key,
      monthLabel: monthNames[d.getMonth()],
      revenue: rev,
      expenses: exp,
      netProfit: rev - exp,
    });
  }

  // Expense breakdown with tax categories
  const taxCatMap = {
    cleaning: 'Schedule E - Cleaning & Maintenance',
    maintenance: 'Schedule E - Repairs',
    utilities: 'Schedule E - Utilities',
    supplies: 'Schedule E - Supplies',
    insurance: 'Schedule E - Insurance',
    mortgage: 'Schedule E - Mortgage Interest',
    taxes: 'Schedule E - Taxes',
    marketing: 'Schedule E - Advertising',
    other: 'Schedule E - Other',
  };
  const totalExp = (expByCatResult.results || []).reduce((s, e) => s + (e.total || 0), 0) || 1;
  const expenseBreakdown = (expByCatResult.results || []).map(e => ({
    category: (e.category || 'Other').charAt(0).toUpperCase() + (e.category || 'other').slice(1),
    amount: e.total || 0,
    percentage: parseFloat(((e.total || 0) / totalExp * 100).toFixed(1)),
    taxCategory: taxCatMap[(e.category || 'other').toLowerCase()] || taxCatMap.other,
  }));

  // Totals
  const totalRevenue = propertyFinancials.reduce((s, p) => s + p.grossRevenue, 0);
  const netProfit = totalRevenue - totalExpenses;
  const avgOccupancy = propertyFinancials.length > 0
    ? Math.round(propertyFinancials.reduce((s, p) => s + p.occupancyPercent, 0) / propertyFinancials.length)
    : 0;
  const avgRevPAR = propertyFinancials.length > 0
    ? Math.round(propertyFinancials.reduce((s, p) => s + p.revPAR, 0) / propertyFinancials.length)
    : 0;

  return json({
    range,
    totals: {
      totalRevenue,
      totalExpenses,
      netProfit,
      avgOccupancy,
      avgRevPAR,
      profitMargin: totalRevenue > 0 ? parseFloat((netProfit / totalRevenue * 100).toFixed(1)) : 0,
      propertyCount: properties.length,
      avgRating: reviewsResult.avg ? parseFloat(parseFloat(reviewsResult.avg).toFixed(1)) : 5.0,
    },
    propertyFinancials,
    monthlyData,
    expenseBreakdown,
    bookingGaps: [],
    weeklyPayouts: [],
  });
}

// ═══════════════════════════════════════════════════════════════
// OWNER DASHBOARD (aggregated owner financial view)
// ═══════════════════════════════════════════════════════════════

async function handleOwnerDashboard(env) {
  const now = new Date();
  const monthStart = now.toISOString().slice(0, 7) + '-01';
  const today = now.toISOString().split('T')[0];
  const yearStart = now.getFullYear() + '-01-01';
  const yearAgo = new Date(now.getTime() - 365 * 86400000).toISOString().split('T')[0];

  // Previous month boundaries for % change calc
  const prevMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
  const prevMonthStart = prevMonthEnd.toISOString().slice(0, 7) + '-01';
  const prevMonthEndStr = prevMonthEnd.toISOString().split('T')[0];

  const [
    curMonthRev, prevMonthRev,
    curMonthExp, prevMonthExp,
    ytdRev, ytdExp,
    upcomingResult, recentExpResult,
    propertiesResult, reviewsResult,
    monthlyRevResult, monthlyExpResult,
    expByCatResult, bookedNightsResult,
    prevBookedNightsResult,
  ] = await Promise.all([
    // Current month revenue (paid invoices)
    env.DB.prepare(
      "SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE status = 'paid' AND issue_date >= ?"
    ).bind(monthStart).first(),
    // Previous month revenue
    env.DB.prepare(
      "SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE status = 'paid' AND issue_date >= ? AND issue_date <= ?"
    ).bind(prevMonthStart, prevMonthEndStr).first(),
    // Current month expenses
    env.DB.prepare(
      "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ?"
    ).bind(monthStart).first(),
    // Previous month expenses
    env.DB.prepare(
      "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ? AND date <= ?"
    ).bind(prevMonthStart, prevMonthEndStr).first(),
    // YTD revenue
    env.DB.prepare(
      "SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE status = 'paid' AND issue_date >= ?"
    ).bind(yearStart).first(),
    // YTD expenses
    env.DB.prepare(
      "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ?"
    ).bind(yearStart).first(),
    // Upcoming bookings (next 10)
    env.DB.prepare(
      "SELECT b.id, b.room_name, b.check_in, b.check_out, b.total, b.status, b.notes, g.name as guest_name, g.email as guest_email FROM bookings b LEFT JOIN guests g ON b.guest_id = g.id WHERE b.check_in >= ? AND b.status != 'cancelled' ORDER BY b.check_in LIMIT 10"
    ).bind(today).all(),
    // Recent expenses (last 10)
    env.DB.prepare(
      "SELECT id, category, description, amount, date, vendor FROM expenses ORDER BY date DESC LIMIT 10"
    ).all(),
    // Properties with booking status
    env.DB.prepare(`
      SELECT p.id, p.name, p.address, p.bedrooms, p.bathrooms, p.max_guests, p.nightly_rate, p.status,
        (SELECT b.id FROM bookings b WHERE b.room_name = p.name AND b.check_in <= ? AND b.check_out > ? AND b.status IN ('confirmed','checked-in') LIMIT 1) as active_booking_id,
        (SELECT g.name FROM guests g JOIN bookings b ON b.guest_id = g.id WHERE b.room_name = p.name AND b.check_in <= ? AND b.check_out > ? AND b.status IN ('confirmed','checked-in') LIMIT 1) as current_guest,
        (SELECT b.check_out FROM bookings b WHERE b.room_name = p.name AND b.check_in <= ? AND b.check_out > ? AND b.status IN ('confirmed','checked-in') LIMIT 1) as current_checkout
      FROM properties p ORDER BY p.id
    `).bind(today, today, today, today, today, today).all(),
    // Average rating + count
    env.DB.prepare("SELECT AVG(rating) as avg, COUNT(*) as count FROM reviews").first(),
    // Monthly revenue (last 12 months)
    env.DB.prepare(
      "SELECT strftime('%Y-%m', issue_date) as month, COALESCE(SUM(total), 0) as revenue FROM invoices WHERE status = 'paid' AND issue_date >= ? GROUP BY month ORDER BY month"
    ).bind(yearAgo).all(),
    // Monthly expenses (last 12 months)
    env.DB.prepare(
      "SELECT strftime('%Y-%m', date) as month, COALESCE(SUM(amount), 0) as expenses FROM expenses WHERE date >= ? GROUP BY month ORDER BY month"
    ).bind(yearAgo).all(),
    // Expense breakdown by category
    env.DB.prepare(
      "SELECT category, COALESCE(SUM(amount), 0) as total FROM expenses WHERE date >= ? GROUP BY category ORDER BY total DESC"
    ).bind(yearStart).all(),
    // Booked nights current month (for occupancy)
    env.DB.prepare(
      "SELECT COALESCE(SUM(CAST(julianday(check_out) - julianday(check_in) AS INTEGER)), 0) as nights FROM bookings WHERE status != 'cancelled' AND check_in >= ?"
    ).bind(monthStart).first(),
    // Booked nights previous month (for occupancy change)
    env.DB.prepare(
      "SELECT COALESCE(SUM(CAST(julianday(check_out) - julianday(check_in) AS INTEGER)), 0) as nights FROM bookings WHERE status != 'cancelled' AND check_in >= ? AND check_in <= ?"
    ).bind(prevMonthStart, prevMonthEndStr).first(),
  ]);

  function pctChange(cur, prev) {
    if (prev === 0) return cur > 0 ? 100 : 0;
    return parseFloat(((cur - prev) / prev * 100).toFixed(1));
  }

  const monthlyEarnings = curMonthRev.total || 0;
  const monthlyExpenses = curMonthExp.total || 0;
  const propCount = (propertiesResult.results || []).length || 1;
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const totalAvailNights = daysInMonth * propCount;
  const curNights = bookedNightsResult.nights || 0;
  const prevNights = prevBookedNightsResult.nights || 0;
  const prevMonthDays = new Date(now.getFullYear(), now.getMonth(), 0).getDate();
  const prevAvailNights = prevMonthDays * propCount;
  const curOccupancy = totalAvailNights > 0 ? curNights / totalAvailNights : 0;
  const prevOccupancy = prevAvailNights > 0 ? prevNights / prevAvailNights : 0;

  // Build monthly chart data (last 12 months)
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const revMap = {};
  for (const r of (monthlyRevResult.results || [])) revMap[r.month] = r.revenue;
  const expMap = {};
  for (const r of (monthlyExpResult.results || [])) expMap[r.month] = r.expenses;

  const revenueChart = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const rev = revMap[key] || 0;
    const exp = expMap[key] || 0;
    revenueChart.push({
      month: monthNames[d.getMonth()],
      revenue: rev,
      expenses: exp,
      net: rev - exp,
    });
  }

  // Expense breakdown by category with colors
  const catColors = {
    cleaning: '#500000', maintenance: '#C4A777', utilities: '#722F37',
    supplies: '#8B4513', insurance: '#A0522D', mortgage: '#2D2D2D',
    taxes: '#4A7C59', marketing: '#6B7280', other: '#9CA3AF',
  };
  const expenseBreakdown = (expByCatResult.results || []).map(e => ({
    name: (e.category || 'Other').charAt(0).toUpperCase() + (e.category || 'other').slice(1),
    value: e.total || 0,
    color: catColors[(e.category || 'other').toLowerCase()] || catColors.other,
  }));

  // Properties with current booking info
  const totalProperties = (propertiesResult.results || []).map(p => ({
    id: p.id,
    name: p.name,
    address: p.address,
    bedrooms: p.bedrooms,
    bathrooms: p.bathrooms,
    max_guests: p.max_guests,
    nightly_rate: p.nightly_rate,
    status: p.active_booking_id ? 'occupied' : (p.status || 'available'),
    current_booking: p.active_booking_id ? {
      guest: p.current_guest,
      check_out: p.current_checkout,
    } : null,
  }));

  // Avg nightly rate from properties
  const avgRate = totalProperties.length > 0
    ? totalProperties.reduce((s, p) => s + (p.nightly_rate || 0), 0) / totalProperties.length
    : 85;

  return json({
    owner_id: 'owner',
    owner_name: 'Steven Palma',
    properties_count: totalProperties.length,
    total_properties: totalProperties,
    monthly_earnings: monthlyEarnings,
    monthly_expenses: monthlyExpenses,
    monthly_net_payout: monthlyEarnings - monthlyExpenses,
    ytd_revenue: ytdRev.total || 0,
    ytd_expenses: ytdExp.total || 0,
    ytd_net_payout: (ytdRev.total || 0) - (ytdExp.total || 0),
    avg_occupancy_rate: curOccupancy,
    avg_nightly_rate: Math.round(avgRate),
    avg_guest_rating: reviewsResult.avg ? parseFloat(parseFloat(reviewsResult.avg).toFixed(1)) : 5.0,
    upcoming_bookings: (upcomingResult.results || []).map(b => ({
      id: b.id,
      guest_name: b.guest_name || 'Unknown',
      guest_email: b.guest_email || '',
      room_name: b.room_name,
      check_in: b.check_in,
      check_out: b.check_out,
      total: b.total || 0,
      status: b.status,
      notes: b.notes,
    })),
    recent_expenses: (recentExpResult.results || []).map(e => ({
      id: e.id,
      category: e.category || 'other',
      description: e.description,
      amount: e.amount || 0,
      date: e.date,
      vendor: e.vendor,
    })),
    pending_maintenance: [],
    revenue_change_percent: pctChange(monthlyEarnings, prevMonthRev.total || 0),
    occupancy_change_percent: pctChange(curOccupancy * 100, prevOccupancy * 100),
    revenue_chart: revenueChart,
    expense_breakdown: expenseBreakdown,
  });
}

// ═══════════════════════════════════════════════════════════════
// ADMIN REVIEWS (enriched review management)
// ═══════════════════════════════════════════════════════════════

async function handleAdminReviews(url, env) {
  // Idempotent ALTER TABLE for missing columns
  const alterStmts = [
    "ALTER TABLE reviews ADD COLUMN title TEXT DEFAULT ''",
    "ALTER TABLE reviews ADD COLUMN property TEXT DEFAULT ''",
    "ALTER TABLE reviews ADD COLUMN status TEXT DEFAULT 'needs_response'",
    "ALTER TABLE reviews ADD COLUMN responded_at TEXT DEFAULT ''",
    "ALTER TABLE reviews ADD COLUMN stay_dates TEXT DEFAULT ''",
    "ALTER TABLE reviews ADD COLUMN sentiment TEXT DEFAULT 'neutral'",
    "ALTER TABLE reviews ADD COLUMN nightly_rate REAL DEFAULT 0",
  ];
  for (const stmt of alterStmts) {
    try { await env.DB.prepare(stmt).run(); } catch (_) {}
  }

  const platform = url.searchParams.get('platform');
  const status = url.searchParams.get('status');
  const rating = url.searchParams.get('rating');

  let sql = `SELECT id, guest_name, rating, text, source, response, created_at,
    COALESCE(title, '') as title,
    COALESCE(property, '') as property,
    COALESCE(status, CASE WHEN response != '' THEN 'responded' ELSE 'needs_response' END) as status,
    COALESCE(responded_at, '') as responded_at,
    COALESCE(stay_dates, '') as stay_dates,
    COALESCE(sentiment, CASE WHEN rating >= 4 THEN 'positive' WHEN rating = 3 THEN 'neutral' ELSE 'negative' END) as sentiment,
    COALESCE(nightly_rate, 0) as nightly_rate
    FROM reviews WHERE 1=1`;

  const binds = [];
  if (platform && platform !== 'all') {
    sql += ' AND source = ?';
    binds.push(platform);
  }
  if (status && status !== 'all') {
    sql += ' AND (status = ? OR (? = "responded" AND response != ""))';
    binds.push(status, status);
  }
  if (rating && Number(rating) > 0) {
    sql += ' AND rating = ?';
    binds.push(Number(rating));
  }

  sql += ' ORDER BY created_at DESC';

  const result = await env.DB.prepare(sql).bind(...binds).all();

  // Map to frontend-compatible format
  const reviews = (result.results || []).map(r => ({
    id: String(r.id),
    guestName: r.guest_name || '',
    property: r.property || '',
    platform: r.source || 'direct',
    rating: r.rating || 5,
    title: r.title || '',
    content: r.text || '',
    date: r.created_at ? r.created_at.split('T')[0] : '',
    status: r.status || (r.response ? 'responded' : 'needs_response'),
    response: r.response || undefined,
    respondedAt: r.responded_at || undefined,
    stayDates: r.stay_dates || '',
    sentiment: r.sentiment || 'neutral',
    nightlyRate: Math.round((r.nightly_rate || 0) * 100),
  }));

  return json({ reviews });
}

async function handleRespondToReview(request, path, env) {
  const id = path.split('/')[2];
  const body = await request.json();
  const { response } = body;
  if (!response) return err('response text required');

  // Ensure columns exist
  try { await env.DB.prepare("ALTER TABLE reviews ADD COLUMN status TEXT DEFAULT 'needs_response'").run(); } catch (_) {}
  try { await env.DB.prepare("ALTER TABLE reviews ADD COLUMN responded_at TEXT DEFAULT ''").run(); } catch (_) {}

  const now = new Date().toISOString();
  await env.DB.prepare(
    'UPDATE reviews SET response = ?, status = ?, responded_at = ? WHERE id = ?'
  ).bind(response, 'responded', now, Number(id)).run();

  return json({ success: true, respondedAt: now });
}

// ═══════════════════════════════════════════════════════════════
// ADMIN CRM (enriched guest management)
// ═══════════════════════════════════════════════════════════════

async function handleCRMGuests(url, env) {
  // Idempotent ALTER TABLE for source column
  try { await env.DB.prepare("ALTER TABLE guests ADD COLUMN source TEXT DEFAULT 'direct'").run(); } catch (_) {}

  const search = url.searchParams.get('search') || '';
  const tier = url.searchParams.get('tier') || 'all';
  const source = url.searchParams.get('source') || 'all';

  const result = await env.DB.prepare(`
    SELECT g.id, g.name, g.email, g.phone, g.notes, g.created_at,
      COALESCE(g.source, 'direct') as source,
      COALESCE(ba.total_stays, 0) as total_stays,
      COALESCE(ba.total_spent, 0) as total_spent,
      COALESCE(ba.last_visit, '') as last_visit,
      COALESCE(ra.avg_rating, 0) as avg_rating
    FROM guests g
    LEFT JOIN (
      SELECT guest_id, COUNT(*) as total_stays, SUM(total) as total_spent, MAX(check_out) as last_visit
      FROM bookings WHERE status != 'cancelled'
      GROUP BY guest_id
    ) ba ON ba.guest_id = g.id
    LEFT JOIN (
      SELECT guest_name, AVG(rating) as avg_rating
      FROM reviews
      GROUP BY guest_name
    ) ra ON ra.guest_name = g.name
    WHERE g.is_owner = 0
    ORDER BY ba.total_spent DESC NULLS LAST
  `).all();

  const guests = (result.results || []).map(g => {
    const stays = g.total_stays || 0;
    let vipTier = 'bronze';
    if (stays >= 10) vipTier = 'platinum';
    else if (stays >= 6) vipTier = 'gold';
    else if (stays >= 3) vipTier = 'silver';

    return {
      id: String(g.id),
      name: g.name || '',
      email: g.email || '',
      phone: g.phone || '',
      totalStays: stays,
      totalSpent: Math.round((g.total_spent || 0) * 100), // convert dollars to cents for frontend
      vipTier,
      lastVisit: g.last_visit ? g.last_visit.split('T')[0] : '',
      avgRating: Math.round((g.avg_rating || 0) * 10) / 10,
      source: g.source || 'direct',
      notes: g.notes || '',
    };
  });

  return json({ guests });
}

async function handleUpdateGuestNotes(request, path, env) {
  const id = path.split('/')[2];
  const body = await request.json();
  const { notes } = body;
  if (notes === undefined) return err('notes field required');

  await env.DB.prepare('UPDATE guests SET notes = ? WHERE id = ?')
    .bind(notes, Number(id)).run();
  return json({ success: true });
}

async function handleCreateCRMGuest(request, env) {
  // Idempotent ALTER TABLE for source column
  try { await env.DB.prepare("ALTER TABLE guests ADD COLUMN source TEXT DEFAULT 'direct'").run(); } catch (_) {}

  const body = await request.json();
  const { name, email, phone, source, notes } = body;
  if (!name) return err('name is required');

  const existing = await env.DB.prepare('SELECT id FROM guests WHERE email = ?').bind(email || '').first();
  if (existing) return err('Guest with this email already exists', 409);

  const result = await env.DB.prepare(
    'INSERT INTO guests (name, email, phone, source, notes, is_owner) VALUES (?, ?, ?, ?, ?, 0)'
  ).bind(name, email || '', phone || '', source || 'direct', notes || '').run();

  return json({ id: result.meta.last_row_id, success: true }, 201);
}

// ═══════════════════════════════════════════════════════════════
// NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════

async function createNotification(env, type, title, message, severity = 'info', actionUrl = null, metadata = {}) {
  try {
    await env.DB.prepare(
      'INSERT INTO notifications (type, title, message, severity, action_url, metadata) VALUES (?, ?, ?, ?, ?, ?)'
    ).bind(type, title, message, severity, actionUrl, JSON.stringify(metadata)).run();
  } catch (e) {
    log('warn', 'Failed to create notification', { type, title, error: e.message });
  }
}

async function handleListNotifications(url, env) {
  const limit = parseInt(url.searchParams.get('limit') || '50');
  const offset = parseInt(url.searchParams.get('offset') || '0');
  const type = url.searchParams.get('type');
  const unreadOnly = url.searchParams.get('unread') === 'true';

  let query = 'SELECT * FROM notifications';
  const conditions = [];
  const binds = [];

  if (type) { conditions.push('type = ?'); binds.push(type); }
  if (unreadOnly) { conditions.push('read = 0'); }
  if (conditions.length > 0) query += ' WHERE ' + conditions.join(' AND ');

  query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
  binds.push(limit, offset);

  const results = await env.DB.prepare(query).bind(...binds).all();
  const total = await env.DB.prepare(
    'SELECT COUNT(*) as count FROM notifications' + (conditions.length > 0 ? ' WHERE ' + conditions.join(' AND ') : '')
  ).bind(...binds.slice(0, conditions.length)).first();

  return json({ notifications: results.results, total: total.count, limit, offset });
}

async function handleUnreadCount(env) {
  const result = await env.DB.prepare('SELECT COUNT(*) as count FROM notifications WHERE read = 0').first();
  return json({ unread: result.count });
}

async function handleMarkRead(path, env) {
  const id = path.split('/')[2];
  await env.DB.prepare('UPDATE notifications SET read = 1 WHERE id = ?').bind(id).run();
  return json({ success: true });
}

async function handleMarkAllRead(env) {
  const result = await env.DB.prepare("UPDATE notifications SET read = 1 WHERE read = 0").run();
  return json({ success: true, marked: result.meta.changes });
}

async function handleDeleteNotification(path, env) {
  const id = path.split('/')[2];
  await env.DB.prepare('DELETE FROM notifications WHERE id = ?').bind(id).run();
  return json({ success: true });
}
