import { useEffect, useState } from 'react';
import { animate, stagger } from 'animejs';
import Camera from './Camera';
import Keychain from './Keychain';
import './Locker.css';

// Import your assets
import lockerBg from '../assets/purple_lockers.png';
import cellPhone from '../assets/final_cellphone.png';
import star from '../assets/final_star(1).png';
import auraLogo from '../assets/final_auralogo.png';

const Locker = ({ onNavigate }) => {
  // 1. ALL STATES AT THE TOP
  const [budget, setBudget] = useState('');
  const [styleRequest, setStyleRequest] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  // 2. THE NAVIGATION FUNCTION
  const handleNextScreen = () => {
    console.log('Going to next screen with:', { budget, styleRequest });
    if (onNavigate) onNavigate(); 
  };

  // 3. ANIMATION EFFECT
  useEffect(() => {
    const timer = setTimeout(() => {
      const elements = document.querySelectorAll('.dynamic-asset');
      if (elements.length > 0) {
        try {
          animate('.dynamic-asset', {
            scale: [0, 1],
            opacity: [0, 1],
            delay: stagger(100),
            ease: 'outElastic(1, .8)'
          });
        } catch (err) {
          console.error('Animation error:', err);
        }
      }
    }, 300);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="viewport-wrapper">
      <div className="locker-canvas">
        {/* STATIC BACKGROUND */}
        <img src={lockerBg} className="locker-bg" alt="lockers" />

        {/* DYNAMIC ASSETS */}
        <img src={star} className="dynamic-asset star-top" alt="star" />
        <img src={cellPhone} className="dynamic-asset flip-phone" alt="phone" />
        <img src={auraLogo} className="aura-header" alt="aura logo" />
        
        {/* CAMERA COMPONENT */}
        <Camera onCapture={handleNextScreen} /> 
        
        <div className="keychain-zone">
          <Keychain />
        </div>

        {/* BOTTOM SECTION: Budget & Style Input */}
        <div className="bottom-input-section">
          <div className="input-group">
            <label>Budget</label>
            <input 
              type="text" 
              placeholder="Enter your budget" 
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
            />
          </div>
          <div className="input-group">
            <label>Style Request</label>
            <textarea 
              placeholder="Describe the style you want..."
              value={styleRequest}
              onChange={(e) => setStyleRequest(e.target.value)}
              rows="3"
            />
          </div>
        </div>

        {/* VOICE RECORDING SECTION */}
        <div className="voice-section">
          <button 
            className={`voice-btn ${isRecording ? 'recording' : ''}`}
            onClick={() => setIsRecording(!isRecording)}
          />
          {isRecording && <span className="recording-indicator">Recording...</span>}
        </div>
      </div>
    </div>
  );
};

export default Locker;