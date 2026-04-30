import { useMemo, useState } from "react";
import { getApiBase, postForm, postJson } from "./api.js";

const initialUpload = {
  file: null,
  device: "gpu",
  conf: "",
  exp_file: "",
  ckpt: "",
  max_frames: "",
  save_result: false
};

const initialWebcam = {
  camid: 0,
  device: "gpu",
  conf: "",
  max_frames: "",
  save_result: false
};

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

export default function App() {
  const apiBase = useMemo(() => getApiBase(), []);
  const [activeTab, setActiveTab] = useState("video");
  const [upload, setUpload] = useState(initialUpload);
  const [uploadStatus, setUploadStatus] = useState("Idle");
  const [uploadOutput, setUploadOutput] = useState("{}");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadOriginalSrc, setUploadOriginalSrc] = useState("");
  const [uploadOutputSrc, setUploadOutputSrc] = useState("");

  const [webcam, setWebcam] = useState(initialWebcam);
  const [webcamStatus, setWebcamStatus] = useState("Idle");
  const [webcamOutput, setWebcamOutput] = useState("{}");
  const [webcamBusy, setWebcamBusy] = useState(false);
  const [webcamOriginalSrc, setWebcamOriginalSrc] = useState("");
  const [webcamOutputSrc, setWebcamOutputSrc] = useState("");

  const updateUpload = (key, value) => {
    setUpload((prev) => ({ ...prev, [key]: value }));
  };

  const updateWebcam = (key, value) => {
    setWebcam((prev) => ({ ...prev, [key]: value }));
  };

  const handleUploadSubmit = async (event) => {
    event.preventDefault();

    if (!upload.file) {
      setUploadStatus("Select a video file first");
      return;
    }

    setUploadBusy(true);
    setUploadStatus("Uploading and running tracking...");
    setUploadOutput("{}");
    setUploadOutputSrc("");

    try {
      // Build FormData (correct for file upload)
      const form = new FormData();
      form.append("file", upload.file);
      form.append("device", upload.device);

      if (upload.conf !== "") form.append("conf", upload.conf);
      if (upload.exp_file) form.append("exp_file", upload.exp_file);
      if (upload.ckpt) form.append("ckpt", upload.ckpt);
      if (upload.max_frames !== "") form.append("max_frames", upload.max_frames);
      form.append("save_result", upload.save_result ? "true" : "false");

      // Call correct API
      const result = await postForm("/tracking/video-upload", form);

      setUploadStatus("Completed");
      setUploadOutput(formatJson(result));

      // Handle output (MinIO or direct URL)
      if (result.output_path) {
          setUploadOutputSrc(result.output_path);
      }

    } catch (error) {
      setUploadStatus("Failed");
      setUploadOutput(formatJson({ error: error.message }));
    } finally {
      setUploadBusy(false);
    }
  };

  const handleWebcamSubmit = async (event) => {
    event.preventDefault();
    setWebcamBusy(true);
    setWebcamStatus("Running live camera tracking...");
    setWebcamOutput("{}");

    try {
      const payload = {
        camid: Number(webcam.camid),
        device: webcam.device,
        save_result: webcam.save_result
      };
      if (webcam.conf !== "") payload.conf = Number(webcam.conf);
      if (webcam.max_frames !== "") payload.max_frames = Number(webcam.max_frames);

      const result = await postJson("/tracking/webcam", payload);
      setWebcamStatus("Completed");
      setWebcamOutput(formatJson(result));
      // If server returns a saved folder or stream path, try to set output
      if (result.saved_folder) {
        const candidate = `${apiBase}${result.saved_folder}/result.mp4`;
        setWebcamOutputSrc(candidate);
      }
      // If server provides a stream or origin URL, set origin
      if (result.stream_url) {
        setWebcamOriginalSrc(result.stream_url.startsWith("http") ? result.stream_url : `${apiBase}${result.stream_url}`);
      } else if (result.stream) {
        setWebcamOriginalSrc(result.stream.startsWith("http") ? result.stream : `${apiBase}${result.stream}`);
      }
    } catch (error) {
      setWebcamStatus("Failed");
      setWebcamOutput(formatJson({ error: error.message }));
    } finally {
      setWebcamBusy(false);
    }
  };

  const stopWebcam = () => {
    setWebcamStatus("Stopped");
    setWebcamOutputSrc("");
    setWebcamOriginalSrc("");
    setWebcamBusy(false);
  };

  return (
    <div className="page">
      <div className="glow"></div>
      <header className="hero">
        <div className="hero-badge">Person Re-ID / Tracking</div>
        <h1>ByteTrack Control Room</h1>
        <p>
          Upload a video or trigger a live camera run. The API returns average FPS so
          you can track performance. API base: <span>{apiBase}</span>
        </p>
        <div className="hero-actions">
          <a className="ghost" href={`${apiBase}/docs`} target="_blank" rel="noreferrer">
            Open API Docs
          </a>
          <a className="solid" href="#upload">
            Upload Video
          </a>
        </div>
      </header>

      <div className="tabs">
        <button className={`tab ${activeTab === "video" ? "active" : ""}`} onClick={() => setActiveTab("video")}>Video</button>
        <button className={`tab ${activeTab === "live" ? "active" : ""}`} onClick={() => setActiveTab("live")}>Live Camera</button>
      </div>

      <main className="grid">
        {activeTab === "video" && (
          <section id="upload" className="card">
          <div className="card-head">
            <h2>Upload Video</h2>
            <span className="tag">Server-side tracking</span>
          </div>
          <form className="form" onSubmit={handleUploadSubmit}>
            <label className="field">
              <span>Video file</span>
              <input
                type="file"
                accept="video/*"
                onChange={(event) => {
                  const f = event.target.files?.[0] || null;
                  updateUpload("file", f);
                  if (f) {
                    try {
                      const url = URL.createObjectURL(f);
                      setUploadOriginalSrc(url);
                    } catch (e) {}
                  } else {
                    setUploadOriginalSrc("");
                  }
                }}
                required
              />
            </label>

            <div className="row">
              <label className="field">
                <span>Device</span>
                <select
                  value={upload.device}
                  onChange={(event) => updateUpload("device", event.target.value)}
                >
                  <option value="gpu">GPU</option>
                  <option value="cpu">CPU</option>
                </select>
              </label>
              <label className="field">
                <span>Confidence</span>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="0.3"
                  value={upload.conf}
                  onChange={(event) => updateUpload("conf", event.target.value)}
                />
              </label>
            </div>

            <div className="row">
              <label className="field">
                <span>Experiment file (optional)</span>
                <input
                  type="text"
                  placeholder="/path/to/exp.py"
                  value={upload.exp_file}
                  onChange={(event) => updateUpload("exp_file", event.target.value)}
                />
              </label>
              <label className="field">
                <span>Checkpoint (optional)</span>
                <input
                  type="text"
                  placeholder="/path/to/ckpt.pth.tar"
                  value={upload.ckpt}
                  onChange={(event) => updateUpload("ckpt", event.target.value)}
                />
              </label>
            </div>

            <div className="row">
              <label className="field">
                <span>Max frames</span>
                <input
                  type="number"
                  min="1"
                  placeholder="Leave empty for full video"
                  value={upload.max_frames}
                  onChange={(event) => updateUpload("max_frames", event.target.value)}
                />
              </label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={upload.save_result}
                  onChange={(event) => updateUpload("save_result", event.target.checked)}
                />
                <span>Save outputs</span>
              </label>
            </div>

            <button className="solid" type="submit" disabled={uploadBusy}>
              {uploadBusy ? "Running..." : "Run Tracking"}
            </button>
          </form>
          <div className="status">{uploadStatus}</div>
          <div className="video-pair">
            <div className="video-card">
              <div className="video-head">Origin</div>
              <video controls src={uploadOriginalSrc} className="video-el" />
            </div>
            <div className="video-card">
              <div className="video-head">Output</div>
              <video controls src={uploadOutputSrc} className="video-el" />
              <div className="field">
                <span>Output URL (optional)</span>
                <input
                  type="text"
                  placeholder="Paste output URL to load"
                  value={uploadOutputSrc}
                  onChange={(e) => setUploadOutputSrc(e.target.value)}
                />
              </div>
            </div>
          </div>
          <pre className="output">{uploadOutput}</pre>
          </section>
        )}

        {activeTab === "live" && (
          <section className="card live-card">
          <div className="card-head">
            <h2>Live Camera</h2>
            <span className="tag">Server device</span>
          </div>
          <form className="form" onSubmit={handleWebcamSubmit}>
            <div className="row">
              <label className="field">
                <span>Camera ID</span>
                <input
                  type="number"
                  min="0"
                  value={webcam.camid}
                  onChange={(event) => updateWebcam("camid", event.target.value)}
                />
              </label>
              <label className="field">
                <span>Device</span>
                <select
                  value={webcam.device}
                  onChange={(event) => updateWebcam("device", event.target.value)}
                >
                  <option value="gpu">GPU</option>
                  <option value="cpu">CPU</option>
                </select>
              </label>
            </div>

            <div className="row">
              <label className="field">
                <span>Confidence</span>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="0.3"
                  value={webcam.conf}
                  onChange={(event) => updateWebcam("conf", event.target.value)}
                />
              </label>
              <label className="field">
                <span>Max frames</span>
                <input
                  type="number"
                  min="1"
                  placeholder="300"
                  value={webcam.max_frames}
                  onChange={(event) => updateWebcam("max_frames", event.target.value)}
                />
              </label>
            </div>

            <label className="toggle">
              <input
                type="checkbox"
                checked={webcam.save_result}
                onChange={(event) => updateWebcam("save_result", event.target.checked)}
              />
              <span>Save outputs</span>
            </label>

            <div style={{display: 'flex', gap: 12}}>
              <button className="solid" type="submit" disabled={webcamBusy}>
                {webcamBusy ? "Running..." : "Start"}
              </button>
              <button type="button" className="ghost" onClick={stopWebcam}>Stop</button>
            </div>
          </form>
          <div className="status">{webcamStatus} {webcamBusy && <span className="badge streaming">● Streaming</span>}</div>
          <div className="live-grid">
            <aside className="live-controls">
              <div className="control-block">
                <label className="field">
                  <span>Camera ID</span>
                  <input type="number" min="0" value={webcam.camid} onChange={(event) => updateWebcam("camid", event.target.value)} />
                </label>
                <label className="field">
                  <span>Device</span>
                  <select value={webcam.device} onChange={(event) => updateWebcam("device", event.target.value)}>
                    <option value="gpu">GPU</option>
                    <option value="cpu">CPU</option>
                  </select>
                </label>
              </div>

              <div className="control-block">
                <label className="field">
                  <span>Confidence</span>
                  <input type="number" min="0" max="1" step="0.01" placeholder="0.3" value={webcam.conf} onChange={(event) => updateWebcam("conf", event.target.value)} />
                </label>
                <label className="field">
                  <span>Max frames</span>
                  <input type="number" min="1" placeholder="300" value={webcam.max_frames} onChange={(event) => updateWebcam("max_frames", event.target.value)} />
                </label>
              </div>

              <div className="control-block">
                <label className="toggle">
                  <input type="checkbox" checked={webcam.save_result} onChange={(event) => updateWebcam("save_result", event.target.checked)} />
                  <span>Save outputs</span>
                </label>
              </div>

              <div className="preview-small">
                <div className="video-head">Origin (server camera)</div>
                <video controls src={webcamOriginalSrc} className="video-el small" />
              </div>
            </aside>

            <section className="live-output-wrap">
              <div className="video-head">Output</div>
              <video controls src={webcamOutputSrc} className="video-el live-output" autoPlay muted playsInline />
              <div className="field">
                <span>Output URL (optional)</span>
                <input type="text" placeholder="Paste output URL to load" value={webcamOutputSrc} onChange={(e) => setWebcamOutputSrc(e.target.value)} />
              </div>
              <pre className="output">{webcamOutput}</pre>
            </section>
          </div>
          <p className="hint">Live camera runs on the server camera device, not the browser webcam.</p>
        </section>
        )}
      </main>

      <footer className="footer">
        <span>ByteTrack UI</span>
        <span>API: /tracking/*</span>
      </footer>
    </div>
  );
}
