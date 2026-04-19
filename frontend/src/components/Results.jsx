import { useEffect } from 'react';
import { animate, stagger } from 'animejs';
import './Locker.css';

// Import Assets
import resultsBg from '../assets/result_page.png';
import cameraResults from '../assets/camera_results.png';
import auraResultsLogo from '../assets/aura_results_final.png';
import notebook from '../assets/notebook.png'; // Make sure names match!
import photostrip from '../assets/photostrip.png';

const Results = ({ onBack }) => {
  useEffect(() => {
    animate('.result-asset', {
      opacity: [0, 1],
      scale: [0.9, 1],
      rotate: (el) => {
        // This gives each item a slightly different "tossed" angle
        if (el.classList.contains('results-photostrip')) return -5;
        if (el.classList.contains('results-notebook')) return 3;
        return 0;
      },
      delay: stagger(150),
      ease: 'outBack'
    });
  }, []);

  return (
    <div className="viewport-wrapper">
      <div className="locker-canvas">
        <img src={resultsBg} className="locker-bg" alt="bg" />

        {/* Top Logo */}
        <img src={auraResultsLogo} className="result-asset results-logo" alt="logo" />

        {/* The Notebook (Left side) */}
        <img src={notebook} className="result-asset results-notebook" alt="notebook" />

        {/* The Camera (Middle-ish) */}
        <img src={cameraResults} className="result-asset results-camera" alt="camera" />

        {/* The Photostrip (Right side) */}
        <img src={photostrip} className="result-asset results-photostrip" alt="photostrip" />

        <button className="result-asset retake-btn" onClick={onBack}>
          RETAKE PHOTO
        </button>
      </div>
    </div>
  );
};

export default Results;