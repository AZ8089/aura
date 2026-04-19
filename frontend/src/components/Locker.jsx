import { useEffect, useRef, useState } from "react";
import { animate, stagger } from "animejs";
import Camera from "./Camera";
import Keychain from "./Keychain";
import "./Locker.css";

import lockerBg from "../assets/purple_lockers.png";
import cellPhone from "../assets/final_cellphone.png";
import star from "../assets/final_star(1).png";
import auraLogo from "../assets/final_auralogo.png";

// In production, VITE_API_BASE can be set to the backend origin if it differs.
// For local dev, the Vite proxy handles /chat and /audio automatically.
const API_BASE = import.meta.env.VITE_API_BASE || "";

const Locker = ({ onResults }) => {
  const [budget, setBudget] = useState("");
  const [styleRequest, setStyleRequest] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [hasAudio, setHasAudio] = useState(false);
  const [hasPhoto, setHasPhoto] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const audioBlobRef = useRef(null);
  const photoBlobRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);

  // Entrance animation — unchanged
  useEffect(() => {
    const timer = setTimeout(() => {
      const elements = document.querySelectorAll(".dynamic-asset");
      if (elements.length > 0) {
        try {
          animate(".dynamic-asset", {
            scale: [0, 1],
            opacity: [0, 1],
            delay: stagger(100),
            ease: "outElastic(1, .8)",
          });
        } catch (err) {
          console.error("Animation error:", err);
        }
      }
    }, 300);
    return () => clearTimeout(timer);
  }, []);

  // Toggle voice recording on/off
  const toggleRecording = async () => {
    if (isRecording) {
      if (
        mediaRecorderRef.current &&
        mediaRecorderRef.current.state !== "inactive"
      ) {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        recordedChunksRef.current = [];

        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm";

        const recorder = new MediaRecorder(stream, { mimeType });
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) recordedChunksRef.current.push(e.data);
        };
        recorder.onstop = () => {
          audioBlobRef.current = new Blob(recordedChunksRef.current, {
            type: mimeType,
          });
          setHasAudio(true);
          stream.getTracks().forEach((t) => t.stop());
        };

        recorder.start(100);
        mediaRecorderRef.current = recorder;
        setIsRecording(true);
      } catch (err) {
        console.error("[Locker] mic access denied:", err);
        setError("Microphone access denied.");
      }
    }
  };

  // Called by Camera shutter — just stores the blob, doesn't submit
  const handlePhotoCapture = (photoBlob) => {
    if (photoBlob) {
      photoBlobRef.current = photoBlob;
      setHasPhoto(true);
    }
  };

  // Explicit submit — called by the Ask Aura button
  const handleSubmit = async () => {
    if (isLoading) return;

    // Stop any active recording so its chunks are flushed
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      await new Promise((r) => setTimeout(r, 200));
    }

    setIsLoading(true);
    setError(null);

    const form = new FormData();
    if (photoBlobRef.current)
      form.append("image", photoBlobRef.current, "photo.jpg");
    if (audioBlobRef.current)
      form.append("audio", audioBlobRef.current, "voice.webm");
    if (styleRequest.trim()) form.append("text", styleRequest.trim());
    if (budget.trim()) form.append("max_budget", budget.trim());

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = await res.json();
      // Attach the captured photo URL so Results can show it on the camera screen
      const photoUrl = photoBlobRef.current
        ? URL.createObjectURL(photoBlobRef.current)
        : null;
      onResults({ ...data, _photoUrl: photoUrl });
    } catch (err) {
      console.error("[Locker] submit error:", err);
      setError(err.message || "Something went wrong. Try again.");
      setIsLoading(false);
    }
  };

  return (
    <div className="viewport-wrapper">
      <div className="locker-canvas">
        <img src={lockerBg} className="locker-bg" alt="lockers" />

        <img src={star} className="dynamic-asset star-top" alt="star" />
        <img src={cellPhone} className="dynamic-asset flip-phone" alt="phone" />
        <img src={auraLogo} className="aura-header" alt="aura logo" />

        {/* Camera — shutter stores the photo blob; submit button sends everything */}
        <Camera onCapture={handlePhotoCapture} isLoading={isLoading} />

        <div className="keychain-zone">
          <Keychain />
        </div>

        <div className="bottom-input-section">
          <div className="input-group">
            <label>Budget</label>
            <input
              type="text"
              placeholder="Enter your budget"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              disabled={isLoading}
            />
          </div>
          <div className="input-group">
            <label>Style Request</label>
            <textarea
              placeholder="Describe the style you want..."
              value={styleRequest}
              onChange={(e) => setStyleRequest(e.target.value)}
              rows="3"
              disabled={isLoading}
            />
          </div>
        </div>

        <div className="voice-section">
          <button
            className={`voice-btn ${isRecording ? "recording" : ""}`}
            onClick={toggleRecording}
            disabled={isLoading}
          />
          {isRecording && (
            <span className="recording-indicator">Recording...</span>
          )}
          {hasAudio && !isRecording && (
            <span className="recording-indicator" style={{ color: "#4caf50" }}>
              Voice ready ✓
            </span>
          )}
        </div>

        {/* Ask Aura submit button — beside the keychain (right side) */}
        <button
          onClick={handleSubmit}
          disabled={isLoading}
          style={{
            position: "absolute",
            top: "680px",
            right: "100px",
            padding: "14px 48px",
            background: isLoading
              ? "#888"
              : "linear-gradient(135deg, #e879a0, #a855f7)",
            color: isLoading ? "#ccc" : "white",
            border: "none",
            borderRadius: "30px",
            fontWeight: "bold",
            fontSize: "16px",
            cursor: isLoading ? "not-allowed" : "pointer",
            boxShadow: isLoading ? "none" : "0 4px 16px rgba(168,85,247,0.45)",
            zIndex: 100,
            whiteSpace: "nowrap",
            opacity: isLoading ? 0.55 : 1,
            transition: "opacity 0.2s, background 0.2s",
            pointerEvents: "auto",
          }}
        >
          {isLoading ? "Aura is cooking... 🍳" : "✦ Ask Aura"}
        </button>

        {error && (
          <div
            style={{
              position: "absolute",
              bottom: "230px",
              left: "50%",
              transform: "translateX(-50%)",
              backgroundColor: "rgba(200,40,40,0.9)",
              color: "white",
              padding: "10px 24px",
              borderRadius: "8px",
              fontSize: "14px",
              zIndex: 100,
              maxWidth: "600px",
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default Locker;
