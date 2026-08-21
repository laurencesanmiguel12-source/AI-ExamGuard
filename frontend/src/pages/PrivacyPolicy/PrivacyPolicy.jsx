import PublicTopbar from "../../components/PublicTopbar";

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-background">
      <PublicTopbar />
      <div className="max-w-screen-md mx-auto px-6 pt-24 pb-20 prose prose-sm">
        <h1 className="font-display font-black text-foreground text-4xl mb-1">Privacy Policy</h1>
        <p className="text-muted-foreground text-sm mb-8">Last updated: August 13, 2026 &middot; Covers the AI ExamGuard web application. For the Tab Monitor browser extension, see its separate policy linked from the download page.</p>

        <h2 className="font-semibold text-lg mt-8 mb-2">Face enrollment</h2>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          Before you can take a proctored exam, you capture a small set of reference photos of
          your face. We use these only to compute a derived mathematical recognition model - the
          raw photos are never stored; only the resulting model is kept, and it is used solely to
          verify your identity during your own proctored exams. Enrolling requires your explicit
          consent, given at the time of enrollment. You can ask your school admin to have your
          enrollment removed.
        </p>

        <h2 className="font-semibold text-lg mt-8 mb-2">What we collect during a proctored exam</h2>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          While an exam session is active, the application uses your webcam to run face
          verification and object detection locally on our server. When a violation is flagged
          (e.g. face lost, phone detected, another person visible), the triggering webcam frame is
          saved as evidence attached to that violation record, viewable by your instructor and any
          school admin, and by you if you file an appeal.
        </p>

        <h2 className="font-semibold text-lg mt-8 mb-2">Evidence retention</h2>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          Violation evidence is automatically deleted 90 days after it's created (sooner is not
          possible while an appeal is pending). School admins can also purge it earlier by hand.
          This is a hard delete of the image file, not a soft flag.
        </p>

        <h2 className="font-semibold text-lg mt-8 mb-2">Using evidence to improve detection models</h2>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          A subset of <strong>phone-detection and multiple-people evidence</strong> (object
          detection only &mdash; frames with no biometric identity purpose) may be used to improve
          our detection models. This happens only after a school admin has individually reviewed
          and approved that specific image for this use through an internal review queue; nothing
          is used automatically. Approved images are copied out for that purpose and, from that
          point on, are retained separately from the 90-day window described above, since they
          become part of a model training set.
        </p>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          <strong>Face-verification evidence (face-lost or identity-mismatch frames) is never used
          to train or improve any model.</strong> That evidence follows the standard 90-day
          retention and deletion described above and nothing else.
        </p>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          If you do not want your exam evidence considered for this review queue at all, contact
          your school admin or email us at the address below and we will exclude your account.
        </p>

        <h2 className="font-semibold text-lg mt-8 mb-2">Other data</h2>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          We store your account details (name, email, student/employee number), exam answers and
          scores, and an audit log of who accessed violation evidence and when. This data is
          scoped to your school and is not shared with other schools on the platform or with any
          third party.
        </p>

        <h2 className="font-semibold text-lg mt-8 mb-2">Contact</h2>
        <p className="text-muted-foreground text-sm leading-relaxed mb-4">
          Questions about this policy, or requests to be excluded from the model-training review
          queue: <a className="text-primary" href="mailto:aueteeap2026@gmail.com">aueteeap2026@gmail.com</a>
        </p>
      </div>
    </div>
  );
}
