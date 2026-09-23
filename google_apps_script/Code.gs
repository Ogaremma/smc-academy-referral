/**
 * Form-bound installable trigger for SMC Academy registration submissions.
 *
 * Script Properties (Project Settings > Script Properties):
 *   BACKEND_WEBHOOK_URL  full webhook URL, e.g.
 *                        https://smc-academy-referral.onrender.com/api/v1/webhooks/google-form
 *   WEBHOOK_SECRET       shared secret sent as the X-Webhook-Secret header
 *   FORM_ID              optional: the registration form id, only needed when
 *                        this script is not bound to the registration form
 *
 * Historical registrations that arrived before the webhook carried the Google
 * Form answers can be re-imported once with backfillHistoricalSubmissions().
 * Run previewHistoricalSubmissions() first to see the report without writing.
 *
 * Setup / recovery entry points, in order:
 *   1. verifyProductionSetup()          - confirms the backend URL + secret and
 *                                         prints the form questions and entry ids
 *   2. installFormSubmitTrigger()       - installs the installable onFormSubmit
 *                                         trigger (required: a simple trigger
 *                                         cannot call the backend)
 *   3. previewHistoricalSubmissions()   - dry run of the historical recovery
 *   4. backfillHistoricalSubmissions()  - applies the recovery
 *
 * runFullRecovery() runs all four steps in order and prints one combined report.
 */

const REFERRAL_QUESTION_HINTS = ["referral", "referred by", "referrer"];
const TELEGRAM_QUESTION_TITLES = ["Telegram Username", "Telegram Handle", "Telegram"];
const EMAIL_QUESTION_HINTS = ["email", "mail"];
const REFERRAL_CODE_PATTERN = /SMC-[A-Z0-9]{4,8}/i;
const BACKFILL_BATCH_SIZE = 50;

function onFormSubmit(e) {
  if (!e || !e.response) {
    throw new Error(
      "This handler requires a Form-bound installable onFormSubmit trigger. " +
        "Run installFormSubmitTrigger() once from the script editor."
    );
  }

  const payload = buildPayload(e.response);
  if (!payload.referral_code) {
    console.log(
      "Submission " + payload.response_id +
        " has no referral code in any answer; no referral webhook was sent."
    );
    return;
  }

  postJson(webhookUrl(), payload);
  console.log(
    "Referral webhook accepted for response " + payload.response_id +
      " (code " + payload.referral_code + ", " + payload.answers.length +
      " answers)."
  );
}

/**
 * Install (or reinstall) the installable form-submit trigger.
 *
 * Apps Script simple triggers cannot call UrlFetchApp, so the registration
 * webhook only fires when this installable trigger exists. Safe to run more
 * than once: previous onFormSubmit triggers are removed first.
 */
function installFormSubmitTrigger() {
  const form = getTargetForm();
  let removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === "onFormSubmit") {
      ScriptApp.deleteTrigger(trigger);
      removed++;
    }
  });
  const trigger = ScriptApp.newTrigger("onFormSubmit").forForm(form).onFormSubmit().create();
  const summary = {
    formTitle: form.getTitle(),
    formId: form.getId(),
    replacedExistingTriggers: removed,
    triggerId: trigger.getUniqueId(),
  };
  console.log(JSON.stringify(summary, null, 2));
  return summary;
}

/**
 * One-call check of the production wiring.
 *
 * Confirms the configured backend URL and secret against the live backend,
 * reports how many webhook deliveries have ever been recorded, resolves a
 * referral code, and prints every form question with its pre-fill entry id so
 * the referral field can be verified.
 */
function verifyProductionSetup(referralCode) {
  const codeToCheck = (referralCode || "SMC-7FELG5").toString().trim();
  const report = { checkedAt: new Date().toISOString(), referralCodeChecked: codeToCheck };

  try {
    report.backendWebhookUrl = webhookUrl();
  } catch (error) {
    report.backendWebhookUrl = "MISSING: " + error.message;
  }
  const secret = PropertiesService.getScriptProperties().getProperty("WEBHOOK_SECRET");
  report.webhookSecretSet = Boolean(secret);
  report.webhookSecretLength = secret ? secret.length : 0;

  report.triggerInstalled = ScriptApp.getProjectTriggers().some(function (trigger) {
    return trigger.getHandlerFunction() === "onFormSubmit";
  });

  try {
    report.backend = postJson(diagnosticsUrl(), { referral_code: codeToCheck });
  } catch (error) {
    report.backend = { error: error.message };
  }

  const form = getTargetForm();
  const items = form.getItems();
  report.form = {
    title: form.getTitle(),
    formId: form.getId(),
    responseCount: form.getResponses().length,
    questions: items.map(function (item) {
      const title = String(item.getTitle() || "");
      const isReferral = REFERRAL_QUESTION_HINTS.some(function (hint) {
        return title.toLowerCase().indexOf(hint) !== -1;
      });
      return {
        entryId: "entry." + item.getId(),
        title: title,
        type: String(item.getType()),
        looksLikeReferralQuestion: isReferral,
      };
    }),
  };

  const configuredEntryId = report.backend && report.backend.referral_entry_id;
  if (configuredEntryId) {
    const match = report.form.questions.filter(function (question) {
      return question.entryId === configuredEntryId;
    });
    report.referralEntryIdCheck = {
      configuredEntryId: configuredEntryId,
      foundInForm: match.length > 0,
      questionTitle: match.length > 0 ? match[0].title : null,
    };
  }

  const referralQuestions = report.form.questions.filter(function (question) {
    return question.looksLikeReferralQuestion;
  });
  if (referralQuestions.length > 0) {
    report.suspectedReferralQuestions = referralQuestions;
  }

  console.log(JSON.stringify(report, null, 2));
  return report;
}

/**
 * Re-import every Google Form response so pre-fix registrations get their full
 * submitted detail. Idempotent: safe to run more than once.
 */
function backfillHistoricalSubmissions() {
  return runHistoricalBackfill(false);
}

/**
 * One-call recovery: verify the wiring, install the submit trigger, preview the
 * historical import, import it, then preview again to confirm the result.
 *
 * Run this once from the Apps Script editor. It never fabricates a referral:
 * submissions whose referral code cannot be resolved are reported as unmatched.
 */
function runFullRecovery(referralCode) {
  const report = {
    startedAt: new Date().toISOString(),
    setup: verifyProductionSetup(referralCode),
    trigger: installFormSubmitTrigger(),
    previewBefore: previewHistoricalSubmissions(),
    backfill: backfillHistoricalSubmissions(),
    previewAfter: previewHistoricalSubmissions(),
  };
  report.finishedAt = new Date().toISOString();
  console.log("FULL RECOVERY REPORT\n" + JSON.stringify(report, null, 2));
  return report;
}

/** Dry run of the backfill: reports what would change without writing. */
function previewHistoricalSubmissions() {
  return runHistoricalBackfill(true);
}

function runHistoricalBackfill(dryRun) {
  const form = getTargetForm();
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

  // Unmatched responses are reported explicitly with the exact reason so an
  // unattributable registration is never silently discarded.
  const unmatchedReasons = details
    .filter(function (item) {
      return item.action === "unmatched";
    })
    .map(function (item) {
      return item.response_id + ": " + item.reason;
    });

  const report = {
    dryRun: dryRun,
    counts: counts,
    unmatchedReasons: unmatchedReasons,
    details: details,
  };
  console.log(JSON.stringify(report, null, 2));
  return report;
}

/** The registration form this script operates on. */
function getTargetForm() {
  try {
    const active = FormApp.getActiveForm();
    if (active) {
      return active;
    }
  } catch (error) {
    // Not bound to a form; fall through to the explicit FORM_ID property.
  }
  const formId = PropertiesService.getScriptProperties().getProperty("FORM_ID");
  if (formId) {
    return FormApp.openById(formId);
  }
  throw new Error(
    "Run this from a script bound to the registration form, or set the " +
      "FORM_ID script property to the registration form id."
  );
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
  // 1. A question that explicitly asks for the referral code / link.
  for (let i = 0; i < answers.length; i++) {
    const question = String(answers[i].question || "").toLowerCase();
    const matchesHint = REFERRAL_QUESTION_HINTS.some(function (hint) {
      return question.indexOf(hint) !== -1;
    });
    if (matchesHint) {
      const code = extractReferralCode(answers[i].answer);
      if (code) {
        return code;
      }
    }
  }
  // The referral link pre-fills the code, so it may sit in a column we do not
  // recognise by title, or inside a longer free-form answer. Scan every answer
  // for the code pattern so a link or a pasted URL still credits the affiliate.
  for (let a = 0; a < answers.length; a++) {
    const code = extractReferralCode(answers[a].answer);
    if (code) {
      return code;
    }
  }
  return "";
}

/** Return the SMC referral code contained in a free-form value, or "". */
function extractReferralCode(value) {
  const text = String(value === null || value === undefined ? "" : value).trim();
  if (!text) {
    return "";
  }
  const match = text.match(REFERRAL_CODE_PATTERN);
  return match ? match[0].toUpperCase() : "";
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

function diagnosticsUrl() {
  return webhookUrl().replace(/\/+$/, "").replace(/\/google-form$/, "/google-form/diagnostics");
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
