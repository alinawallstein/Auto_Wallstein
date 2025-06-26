import { motion } from "framer-motion";
import "./App.css";
import carImage from "/Users/alinawallstein/Desktop/Auto_Wallstein/auto-wallstein/public/Auto_wallstein_logo.png"; // Du kannst hier später dein echtes Auto-Logo/Bild einfügen

function App() {
  return (
    <div className="app">
      {/* Titeltext */}
      <motion.h1
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
        className="title"
      >
        Willkommen bei Auto Wallstein
      </motion.h1>

      {/* Auto fährt ins Bild */}
      <motion.img
        src={carImage}
        alt="Auto Wallstein"
        initial={{ x: "-100vw" }}
        animate={{ x: 0 }}
        transition={{ type: "spring", stiffness: 60 }}
        className="car"
      />

      {/* Button */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        className="cta-button"
      >
        Mehr erfahren
      </motion.button>
    </div>
  );
}

export default App;