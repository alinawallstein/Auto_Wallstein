// AutoWallsteinWebseite/netlify/senden.js
// oder netlify/functions/senden.js – je nach Netlify-Einstellung

const nodemailer = require("nodemailer");

exports.handler = async (event, context) => {
  // Nur POST zulassen
  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      body: "Method Not Allowed",
    };
  }

  try {
    // Formulardaten kommen als x-www-form-urlencoded
    const params = new URLSearchParams(event.body);

    const vorname   = params.get("fname")    || "";
    const nachname  = params.get("lname")    || "";
    const email     = params.get("email")    || "";
    const telefon   = params.get("phone")    || "";
    const interesse = params.get("interest") || "";
    const nachricht = params.get("message")  || "";

    // --- E-Mail-Text wie in deinem PHP ---
    const betreff = "Neue Kontaktanfrage über die Webseite";

    const inhalt = `
Es ist eine neue Kontaktanfrage über das Formular auf der Auto-Wallstein-Webseite eingegangen:

Name: ${vorname} ${nachname}
E-Mail: ${email}
Telefon: ${telefon}
Interesse: ${interesse}

Nachricht:
${nachricht}
`.trim();

    // --- Nodemailer-Transporter einrichten ---
    // Diese Daten trägst du in Netlify als Environment Variables ein
    // (Site settings -> Environment variables)
    const transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST,       // z.B. "smtp.strato.de" o.ä.
      port: Number(process.env.SMTP_PORT) || 587,
      secure: false,                     // meist false bei Port 587
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS,
      },
    });

    // Mail abschicken
    await transporter.sendMail({
      from: `"Auto Wallstein Webseite" <${process.env.SMTP_FROM}>`,
      to: process.env.SMTP_TO, // deine Zieladresse, z.B. verkauf@auto-wallstein.de
      subject: betreff,
      text: inhalt,
    });

    // Antwort an den Browser – kleine Danke-Seite
    return {
      statusCode: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
      },
      body: `
        <!doctype html>
        <html lang="de">
        <head>
          <meta charset="utf-8" />
          <title>Nachricht gesendet</title>
          <meta http-equiv="refresh" content="5;url=/kontakt.html" />
          <style>
            body {
              font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              padding: 2rem;
              text-align: center;
            }
          </style>
        </head>
        <body>
          <h1>Vielen Dank für Ihre Nachricht!</h1>
          <p>Wir melden uns so schnell wie möglich bei Ihnen.</p>
          <p>Sie werden in wenigen Sekunden zurück zur Kontaktseite geleitet.</p>
        </body>
        </html>
      `,
    };
  } catch (err) {
    console.error("Fehler beim Senden der E-Mail:", err);
    return {
      statusCode: 500,
      body: "Fehler: Die Nachricht konnte nicht gesendet werden.",
    };
  }
};