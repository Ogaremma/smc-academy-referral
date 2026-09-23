/**
 * Form-bound installable trigger for SMC Academy registration submissions.
 *
 * Script Properties (Project Settings > Script Properties):
 *   BACKEND_WEBHOOK_URL  full webhook URL, e.g.
 *                        https://smc-academy-referral.onrender.com/api/v1/webhooks/google-form
 *   WEBHOOK_SECRET       shared secret sent as the X-Webhook-Secret header
 *
 * Historical registrations that arrived before the webhook carried the Google
 * Form answers can be re-imported once with backfillHistoricalSubmissions().
 * Run previewHistoricalSubmissions() first to see the report without writing.
 */

const REFERRAL_QUESTION_HINTS = ["referral", "referred by", "referrer"];
const TELEGRAM_QUESTION_TITLES = ["Telegram Username", "Telegram Handle", "Telegram"];
const EMAIL_QUESTION_HINTS = ["email", "mail"];
const REFERRAL_CODE_PATTERN = /SMC-[A-Z0-9]{4,8}/i;
const BACKFILL_BATCH_SIZE = 50;

function onFormSubmit(e) {
  if (!e || !e.response) {
    throw new Error("This handler requires a Form-bound onFormSubmit event.");
  }

  const payload = buildPayload(e.response);
  if (!payload.referral_code) {
    console.log("Submission has no referral code; no referral webhook was sent.");
    return;
  }

  postJson(webhookUrl(), payload);
  console.log("Referral webhook accepted for response " + payload.response_id + ".");
}

/**
 * Re-import every Google Form response so pre-fix registrations get their full
 * submitted detail. Idempotent: safe to run more than once.
 */
function backfillHistoricalSubmissions() {
  return runHistoricalBackfill(false);
}

/** Dry run of the backfill: reports what would change without writing. */
function previewHistoricalSubmissions() {
  return runHistoricalBackfill(true);
}

function runHistoricalBackfill(dryRun) {
  const form = FormApp.getActiveForm();
  if (!form) {
    throw new Error("Run this from a script bound to the registration form.");
  }
  const responses = form.getResponses();
  const counts = { total: 0, created: 0, enriched: 0, unchanged: 0, unmatched: 0 };
  const details = [];

  for (let start = 0; start < responses.length; start += BACKFILL_BATCH_SIZE) {
    const batch = responses.slice(start, start + BACKFILL_BATCH_SIZE).map(function (formResponse) {
      return buildPayload(formResponse);
    });
    const result = postJson(reconcileUrl(), { dry_run: dryRun, responses: batch });
    counts.total += result.total || batch.length;
    counts.created += result.created || 0;
    counts.enriched += result.enriched || 0;
    counts.unchanged += result.unchanged || 0;
    counts.unmatched += result.unmatched || 0;
    (result.results || []).forEach(function (item) {
      details.push(item);
    });
  }

  const report = { dryRun: dryRun, counts: counts, details: details };
  console.log(JSON.stringify(report, null, 2));
  return report;
}

/** Build the webhook payload for a single form response. */
function buildPayload(formResponse) {
  const itemResponses = formResponse.getItemResponses();
  const answers = extractAnswerList(itemResponses);
  const referralCode = findReferralCode(answers);

  let candidateTelegramHandle = findKnownAnswer(answers, TELEGRAM_QUESTION_TITLES);
  if (!candidateTelegramHandle) {
    candidateTelegramHandle = findAnswerByHint(answers, ["telegram", "handle"]);
  }

  let candidateEmail = "";
  try {
    candidateEmail = formResponse.getRespondentEmail() || "";
  } catch (error) {
    candidateEmail = "";
  }
  if (!candidateEmail) {
    candidateEmail = findAnswerByHint(answers, EMAIL_QUESTION_HINTS);
  }

  return {
    response_id: formResponse.getId(),
    submitted_at: formResponse.getTimestamp().toISOString(),
    referral_code: referralCode ? referralCode.trim().toUpperCase() : "",
    candidate_email: candidateEmail || null,
    candidate_telegram_handle: candidateTelegramHandle || null,
    // Every submitted answer, including file uploads, so the full registration
    // (and payment proof) is available to the affiliate and to admins.
    answers: answers
  };
}

function extractAnswerList(itemResponses) {
  const answers = [];
  itemResponses.forEach(function (itemResponse) {
    const question = String(itemResponse.getItem().getTitle() || "").trim();
    const answer = readAnswer(itemResponse);
    if (question && answer) {
      answers.push({ question: question, answer: answer });
    }
  });
  return answers;
}

function readAnswer(itemResponse) {
  const raw = itemResponse.getResponse();
  if (isFileUpload(itemResponse)) {
    return fileUploadLinks(raw);
  }
  if (Array.isArray(raw)) {
    return raw.join(", ");
  }
  return String(raw === null || raw === undefined ? "" : raw).trim();
}

function isFileUpload(itemResponse) {
  try {
    return itemResponse.getItem().getType() === FormApp.ItemType.FILE_UPLOAD;
  } catch (error) {
    return false;
  }
}

/** Preserve a usable link for file-upload answers (Google returns Drive file IDs). */
function fileUploadLinks(raw) {
  const values = Array.isArray(raw) ? raw : [raw];
  const links = [];
  values.forEach(function (value) {
    const text = String(value === null || value === undefined ? "" : value).trim();
    if (!text) {
      return;
    }
    if (/^https?:\/\//i.test(text)) {
      links.push(text);
      return;
    }
    links.push("https://drive.google.com/open?id=" + encodeURIComponent(text));
  });
  return links.join(", ");
}

function findReferralCode(answers) {
  for (let i = 0; i < answers.length; i++) {
    const question = answers[i].question.toLowerCase();
    const matchesHint = REFERRAL_QUESTION_HINTS.some(function (hint) {
      return question.indexOf(hint) !== -1;
    });
    if (matchesHint) {
      const value = String(answers[i].answer || "").trim();
      if (value) {
        return value;
      }
    }
  }
  // The referral link pre-fills the code, so it may sit in a column we do not
  // recognise by title. Fall back to scanning for the code pattern.
  for (let a = 0; a < answers.length; a++) {
    const match = String(answers[a].answer || "").match(REFERRAL_CODE_PATTERN);
    if (match) {
      return match[0];
    }
  }
  return "";
}

function findKnownAnswer(answers, titles) {
  for (let i = 0; i < titles.length; i++) {
    const target = titles[i].toLowerCase();
    for (let a = 0; a < answers.length; a++) {
      if (answers[a].question.trim().toLowerCase() === target) {
        return answers[a].answer;
      }
    }
  }
  return "";
}

function findAnswerByHint(answers, hints) {
  for (let a = 0; a < answers.length; a++) {
    const question = answers[a].question.toLowerCase();
    const matchesHint = hints.some(function (hint) {
      return question.indexOf(hint) !== -1;
    });
    if (matchesHint) {
      return answers[a].answer;
    }
  }
  return "";
}

function scriptProperty(name) {
  const value = PropertiesService.getScriptProperties().getProperty(name);
  if (!value) {
    throw new Error("Missing " + name + " Script Property.");
  }
  return value;
}

function webhookUrl() {
  return scriptProperty("BACKEND_WEBHOOK_URL");
}

function reconcileUrl() {
  return webhookUrl().replace(/\/+$/, "").replace(/\/google-form$/, "/google-form/reconcile");
}

function postJson(url, body) {
  const response = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    headers: { "X-Webhook-Secret": scriptProperty("WEBHOOK_SECRET") },
    payload: JSON.stringify(body),
    muteHttpExceptions: true
  });
  const statusCode = response.getResponseCode();
  const text = response.getContentText();
  if (statusCode < 200 || statusCode >= 300) {
    throw new Error("Backend request failed with HTTP " + statusCode + ": " + text);
  }
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    return { raw: text };
  }
}
