import { useEffect, useState } from "react";
import { useSchoolNav } from "../../hooks/useSchoolNav";
import { Camera, CheckCircle, Trash2 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { getStudents } from "../../api/students";
import { enrollFace } from "../../api/faceEnrollment";
import useCamera from "../../hooks/useCamera";
import Card from "../../components/ui/Card";
import SectionTag from "../../components/ui/SectionTag";

const TARGET_CAPTURES = 5;
const MIN_CAPTURES = 3;

export default function FaceEnrollment() {
  const { user } = useAuth();
  const navigate = useSchoolNav();

  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [captures, setCaptures] = useState([]);
  const [previewUrls, setPreviewUrls] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const { videoRef, error: cameraError, ready, captureFrame } = useCamera(true);

  // One object URL per capture, revoked whenever the capture list changes or the page leaves -
  // creating a fresh URL inline in the render below (the previous approach) leaked a growing
  // number of blob URLs, since createObjectURL was called again on every re-render with no
  // matching revokeObjectURL.
  useEffect(() => {
    const urls = captures.map((blob) => URL.createObjectURL(blob));
    setPreviewUrls(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [captures]);

  useEffect(() => {
    getStudents()
      .then((students) => setStudent(students.find((s) => s.user_id === user.id) ?? null))
      .finally(() => setLoading(false));
  }, [user.id]);

  async function handleCapture() {
    const blob = await captureFrame();
    if (blob) setCaptures((c) => [...c, blob]);
  }

  function handleRemove(i) {
    setCaptures((c) => c.filter((_, idx) => idx !== i));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    try {
      const data = await enrollFace(student.id, captures);
      setResult(data);
      setCaptures([]);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Enrollment failed. Try again with clearer photos.");
    } finally {
      setSubmitting(false);
    }
  }

  const alreadyEnrolled = student?.face_model_path != null;

  return (
    <div className="min-h-screen bg-background px-6 py-10 max-w-2xl mx-auto">
      <SectionTag text="Biometric Setup" />
      <h2 className="font-display font-black text-foreground text-4xl mb-1">Face Enrollment</h2>
      <p className="text-muted-foreground text-sm mb-8">
        Capture {TARGET_CAPTURES} clear photos of your face. We store only a derived recognition
        model — never the raw photos.
      </p>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {!loading && !student && (
        <Card className="p-8 text-center">
          <p className="text-sm text-muted-foreground">
            Your account isn't linked to a student record yet. Ask an admin to provision one.
          </p>
        </Card>
      )}

      {!loading && student && (
        <>
          {alreadyEnrolled && !result && (
            <div className="mb-6 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
              You're already enrolled. Capturing new photos below will replace your existing enrollment.
            </div>
          )}

          {result ? (
            <Card className="p-8 text-center">
              <CheckCircle className="w-12 h-12 mx-auto mb-4 text-emerald-500" />
              <h3 className="font-display font-black text-2xl text-foreground mb-1">Enrollment Complete</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Trained on {result.samples_used} of your captured photos.
              </p>
              <button
                onClick={() => navigate("/dashboard")}
                className="bg-primary hover:bg-primary/90 text-white px-4 py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
              >
                Back to Dashboard
              </button>
            </Card>
          ) : (
            <Card className="overflow-hidden">
              <div className="relative aspect-[4/3] bg-secondary flex items-center justify-center">
                {cameraError ? (
                  <div className="text-center px-6">
                    <p className="text-sm text-muted-foreground">Camera unavailable</p>
                    <p className="text-[11px] font-mono text-muted-foreground mt-1">{cameraError}</p>
                  </div>
                ) : (
                  <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                )}
              </div>

              <div className="p-6">
                {error && (
                  <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-600">
                    {error}
                  </div>
                )}

                <div className="flex items-center justify-between mb-4">
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-widest">
                    {captures.length}/{TARGET_CAPTURES} captured
                  </span>
                  <button
                    onClick={handleCapture}
                    disabled={!ready || captures.length >= TARGET_CAPTURES}
                    className="flex items-center gap-1.5 bg-primary hover:bg-primary/90 disabled:opacity-40 text-white text-[11px] font-mono uppercase tracking-wider px-3 py-2 rounded-lg transition-colors"
                  >
                    <Camera className="w-3.5 h-3.5" /> Capture
                  </button>
                </div>

                {captures.length > 0 && (
                  <div className="grid grid-cols-5 gap-2 mb-6">
                    {captures.map((blob, i) => (
                      <div key={i} className="relative aspect-square rounded-lg overflow-hidden border border-border">
                        <img src={previewUrls[i]} alt="" className="w-full h-full object-cover" />
                        <button
                          onClick={() => handleRemove(i)}
                          className="absolute top-0.5 right-0.5 bg-black/60 rounded p-0.5"
                          aria-label="Remove"
                        >
                          <Trash2 className="w-3 h-3 text-white" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={handleSubmit}
                  disabled={captures.length < MIN_CAPTURES || submitting}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white py-2.5 rounded-xl text-sm font-mono uppercase tracking-widest transition-colors"
                >
                  {submitting ? "Submitting…" : `Submit Enrollment (min ${MIN_CAPTURES})`}
                </button>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
