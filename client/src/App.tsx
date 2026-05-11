import { motion } from "framer-motion";
import "./App.css";

const cards = [
  {
    title: "Jahreswagen",
    text: "Ausgewaehlte Mercedes-Benz Fahrzeuge mit transparenter Beratung.",
  },
  {
    title: "Finanzierung",
    text: "Planbare Raten, klare Laufzeiten und Angebote passend zur Situation.",
  },
  {
    title: "Export",
    text: "Unterstuetzung bei Zulassung, Kennzeichen und weltweitem Versand.",
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0 },
};

function App() {
  return (
    <main className="app-shell">
      <motion.nav
        className="topbar"
        initial={{ opacity: 0, y: -18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55 }}
      >
        <a className="brand" href="/">
          <img src="/Auto_wallstein_logo.png" alt="Auto Wallstein Logo" />
          <span>Auto Wallstein</span>
        </a>
        <div className="nav-actions">
          <a href="mailto:verkauf@auto-wallstein.de">E-Mail</a>
          <a className="nav-phone" href="tel:+496104406770">
            Anrufen
          </a>
        </div>
      </motion.nav>

      <section className="hero">
        <motion.div
          className="hero-copy"
          initial="hidden"
          animate="visible"
          transition={{ staggerChildren: 0.12 }}
        >
          <motion.p className="eyebrow" variants={fadeUp}>
            Mercedes-Benz Jahres- & Geschaeftswagen
          </motion.p>
          <motion.h1 variants={fadeUp}>
            Premium-Fahrzeuge mit persoenlicher Beratung in Heusenstamm.
          </motion.h1>
          <motion.p className="hero-text" variants={fadeUp}>
            Finden Sie Ihren naechsten Mercedes-Benz mit Zugriff auf tausende
            Fahrzeuge, fairer Finanzierung und unkomplizierter Abwicklung.
          </motion.p>
          <motion.div className="hero-actions" variants={fadeUp}>
            <a className="primary-btn" href="/fahrzeuge.html">
              Fahrzeuge ansehen
            </a>
            <a className="secondary-btn" href="/kontakt.html">
              Kontakt aufnehmen
            </a>
          </motion.div>
        </motion.div>

        <motion.div
          className="hero-media"
          initial={{ opacity: 0, x: 42, scale: 0.96 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ duration: 0.75, delay: 0.15 }}
        >
          <img src="/damals.jpg" alt="Auto Wallstein Fahrzeughistorie" />
          <motion.div
            className="floating-note"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.65 }}
          >
            <strong>Seit 1955</strong>
            <span>Erfahrung im Fahrzeughandel</span>
          </motion.div>
        </motion.div>
      </section>

      <motion.section
        className="service-grid"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
        transition={{ staggerChildren: 0.12 }}
      >
        {cards.map((card) => (
          <motion.article className="service-card" variants={fadeUp} key={card.title}>
            <h2>{card.title}</h2>
            <p>{card.text}</p>
          </motion.article>
        ))}
      </motion.section>
    </main>
  );
}

export default App;
