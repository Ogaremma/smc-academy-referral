/**
 * Form-bound installable trigger for SMC Academy registration submissions.
 * Configure BACKEND_WEBHOOK_URL and WEBHOOK_SECRET in Apps Script Properties.
 */

const REFERRAL_QUESTION_TITLE = "Referral Code";
const TELEGRAM_QUESTION_TITLES = ["Telegram Username", "Telegram Handle"];

function onFormSubmit(e) {
  if (!e || !e.response) {
    throw new Error("This handler requires a Form-bound onFormSubmit event.");
  }

  const properties = PropertiesService.getScriptProperties();
  const backendWebhookUrl = properties.getProperty("BACKEND_WEBHOOK_URL");
  const webhookSecret = properties.getProperty("WEBHOOK_SECRET");
  if (!backendWebhookUrl || !webhookSecret) {
    throw new Error("Missing BACKEND_WEBHOOK_URL or WEBHOOK_SECRET Script Property.");
  }

  const formResponse = e.response;
  const answers = extractAnswers(formResponse.getItemResponses());
  const referralCode = answers[REFERRAL_QUESTION_TITLE.toLowerCase()] || "";
  if (!referralCode) {
    console.log("Submission has no referral code; no referral webhook was sent.");
    return;
  }

  let candidateTelegramHandle = "";
  for (let i = 0; i < TELEGRAM_QUESTION_TITLES.length; i++) {
    candidateTelegramHandle = answers[TELEGRAM_QUESTION_TITLES[i].toLowerCase()] || "";
    if (candidateTelegramHandle) break;
  }

  const payload = {
    response_id: formResponse.getId(),
    submitted_at: formResponse.getTimestamp().toISOString(),
    referral_code: referralCode.trim().toUpperCase(),
    candidate_email: formResponse.getRespondentEmail() || null,
    candidate_telegram_handle: candidateTelegramHandle || null
  };

  const response = UrlFetchApp.fetch(backendWebhookUrl, {
    method: "post",
    contentType: "application/json",
    headers: { "X-Webhook-Secret": webhookSecret },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const statusCode = response.getResponseCode();
  if (statusCode < 200 || statusCode >= 300) {
    throw new Error("Referral webhook failed with HTTP " + statusCode + ".");
  }
  console.log("Referral webhook accepted for response " + formResponse.getId() + ".");
}

function extractAnswers(itemResponses) {
  const answers = {};
  itemResponses.forEach(function(itemResponse) {
    const title = itemResponse.getItem().getTitle().trim().toLowerCase();
    const response = itemResponse.getResponse();
    answers[title] = Array.isArray(response) ? response.join(", ") : String(response || "").trim();
  });
  return answers;
}
