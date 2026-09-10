import { useState } from "react";
import { Upload, Download, ChevronDown, ChevronRight, CheckCircle2, Eye, FileSpreadsheet } from "lucide-react";
import Card from "../../components/ui/Card";
import { importSetupCsv, previewSetupCsv } from "../../api/setupImport";

// A real, importable example rather than placeholder text - one row of each type, in an order
// that demonstrates the dependency (the subject names the course above it, the instructor names
// the subject). Someone can replace the values and upload it without reading anything else.
// Every layer in one file, in the order the program flow runs. The last four row types are
// what turns a catalogue into a school that can actually run an exam: two students, two
// sections of one subject (which is what tells two instructors of it apart), and the class
// list that an exam inherits.
const TEMPLATE =
  "type,code,name,course_code,employee_number,email,password,first_name,last_name,subject_codes,capacity,schedule\n" +
  "course,BSCS,BS Computer Science,,,,,,,,,\n" +
  "course,BSIT,BS Information Technology,,,,,,,,,\n" +
  "subject,CS-101,Introduction to Programming,BSCS,,,,,,,,\n" +
  "subject,CS-201,Data Structures,BSCS,,,,,,,,\n" +
  "subject,IT-101,Web Systems,BSIT,,,,,,,,\n" +
  "instructor,,,,EMP-001,ana.cruz@school.edu,ChangeMe123!,Ana,Cruz,CS-101;CS-201,,\n" +
  "instructor,,,,EMP-002,ben.reyes@school.edu,ChangeMe123!,Ben,Reyes,IT-101,,\n" +
  "student,,,BSCS,,sam.diaz@school.edu,ChangeMe123!,Sam,Diaz,,,\n" +
  "student,,,BSCS,,mia.lopez@school.edu,ChangeMe123!,Mia,Lopez,,,\n" +
  "section,A,,,EMP-001,,,,,CS-101,40,MWF 9:00-10:30\n" +
  "section,B,,,EMP-002,,,,,CS-101,40,TTh 13:00-14:30\n" +
  "enrollment,A,,,,sam.diaz@school.edu,,,,CS-101,,\n" +
  "enrollment,A,,,,mia.lopez@school.edu,,,,CS-101,,\n";

const COLUMNS = [
  ["type", "Which kind of row this is: course, subject, instructor, student, section or enrollment. Required on every row."],
  ["code", "The course or subject code (BSCS, CS-101) — or, on section and enrollment rows, the section's own code, e.g. A."],
  ["name", "The full name. Course and subject rows only."],
  ["course_code", "Which course this belongs to, by its code. Subject rows and student rows."],
  ["employee_number", "Your school's own staff ID. Instructor rows create it; section rows use it to say who teaches the class."],
  ["email", "Sign-in address. Instructor and student rows create it; enrollment rows use it to name the student, because student numbers are generated and you would not know them yet."],
  ["password", "A starting password, on instructor and student rows. Tell them to change it after first sign-in."],
  ["first_name / last_name", "Instructor and student rows."],
  ["subject_codes", "On instructor rows, every subject they teach, separated by semicolons. On section and enrollment rows, the ONE subject the class is of."],
  ["capacity / schedule", "Section rows only, both optional. Capacity is for reference — it does not block enrolment."],
];

// The four steps, stated once. The panel asked for a visible process flow rather than a file
// input and a button - the sequence is not guessable, and the checking step is the one people
// skip when nothing tells them it exists.
const STEPS = [
  ["Download the template", "One row per course, subject and instructor, with a working example already filled in."],
  ["Fill it in with Excel", "Open the file in Excel, replace the example rows with your own, then Save As → CSV UTF-8."],
  ["Check the file", "Runs the real import and throws the result away, so you see what would happen — duplicates, bad rows and all — before anything is written."],
  ["Import", "Only what the check showed. Re-uploading later is safe: anything that already exists is skipped."],
];

export default function SetupImportPanel() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [importing, setImporting] = useState(false);
  const [checking, setChecking] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  function downloadTemplate() {
    const url = URL.createObjectURL(new Blob([TEMPLATE], { type: "text/csv;charset=utf-8;" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "examguard_setup_template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handleCheck() {
    if (!file) return;
    setChecking(true);
    setError("");
    setResult(null);
    try {
      setResult(await previewSetupCsv(file));
    } catch (err) {
      setError(err.response?.data?.detail ?? "Couldn't read that file.");
    } finally {
      setChecking(false);
    }
  }

  async function handleImport() {
    if (!file) return;
    setImporting(true);
    setError("");
    setResult(null);
    try {
      setResult(await importSetupCsv(file));
    } catch (err) {
      setError(err.response?.data?.detail ?? "Couldn't import that file.");
    } finally {
      setImporting(false);
    }
  }

  // Every layer the importer creates, in program-flow order. Kept as one list so a new row type
  // is added in one place rather than in a total, a breakdown and a label that can disagree.
  const CREATED = [
    ["created_courses", "course", "courses"],
    ["created_subjects", "subject", "subjects"],
    ["created_instructors", "instructor", "instructors"],
    ["created_students", "student", "students"],
    ["created_sections", "section", "sections"],
    ["created_enrollments", "enrolment", "enrolments"],
  ];
  const total = result
    ? CREATED.reduce((sum, [key]) => sum + (result[key] ?? 0), 0)
    : 0;
  const breakdown = result
    ? CREATED.filter(([key]) => (result[key] ?? 0) > 0).map(
        ([key, one, many]) => `${result[key]} ${result[key] === 1 ? one : many}`
      )
    : [];
  const isPreview = result?.preview === true;

  return (
    // No heading of its own: this now sits under the Bulk Import page's PageHeader, which says
    // the same thing in the place every other screen says it.
    <div>
      <Card className="p-6">
        <ol className="mb-5 grid gap-3 sm:grid-cols-2">
          {STEPS.map(([title, detail], i) => (
            <li key={title} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border bg-secondary font-mono text-[11px] font-semibold text-muted-foreground">
                {i + 1}
              </span>
              <div>
                <div className="text-sm font-semibold text-foreground">{title}</div>
                <p className="text-sm text-muted-foreground">{detail}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mb-5 flex gap-2.5 rounded-xl border border-border bg-secondary px-4 py-3">
          <FileSpreadsheet className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">Use Excel, and save as CSV UTF-8.</span>{" "}
            Excel's plain &ldquo;CSV&rdquo; option mangles accented names and long ID numbers, and a
            file saved from Notepad usually loses its column headings. Keep every column even where
            it is blank &mdash; a course row leaves the instructor columns empty and vice versa.
          </p>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-4">
          <button
            onClick={downloadTemplate}
            className="flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-primary transition-colors hover:text-primary/80"
          >
            <Download className="h-3.5 w-3.5" /> Download template
          </button>
          <button
            onClick={() => setShowGuide((v) => !v)}
            aria-expanded={showGuide}
            className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
          >
            {showGuide ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            Column guide
          </button>
        </div>

        {showGuide && (
          <div className="mb-4 rounded-xl border border-border bg-secondary/40 p-4">
            <dl className="space-y-2.5">
              {COLUMNS.map(([column, rule]) => (
                <div key={column} className="grid grid-cols-1 gap-1 sm:grid-cols-[180px_1fr] sm:gap-3">
                  <dt className="pt-0.5 font-mono text-[11px] text-foreground/80">{column}</dt>
                  <dd className="text-sm text-muted-foreground">{rule}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-4 border-t border-border pt-3 text-sm text-muted-foreground">
              <p className="mb-2">
                <span className="font-semibold text-foreground">
                  Sections and enrolments go into whichever term is running.
                </span>{" "}
                They do not name a term, so open and activate one on the Academic Calendar before
                uploading a sheet that contains them. A registrar filling this in is describing
                this semester, and repeating the term on three hundred rows only invites one of
                them to disagree with the rest.
              </p>
              <p>
                Leave unused columns empty — every row keeps all the columns, most of them blank.
                Save as <span className="font-mono text-foreground/80">CSV UTF-8</span>.
              </p>
              <p className="mt-2">
                Uploading the same file twice is safe: anything that already exists is skipped
                rather than duplicated, so you can add rows to your sheet and re-upload it.
              </p>
            </div>
          </div>
        )}

        <input
          type="file"
          accept=".csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
            setError("");
          }}
          aria-label="Choose a setup CSV file"
          className="mb-4 block text-sm text-foreground"
        />

        {error && (
          <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleCheck}
            disabled={!file || checking || importing}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-[12px] font-mono uppercase tracking-wider text-white transition-colors hover:bg-primary/90 disabled:opacity-40"
          >
            <Eye className="h-4 w-4" /> {checking ? "Checking…" : "Check this file"}
          </button>
          {/* Available without checking first - an admin re-uploading a sheet they have already
              checked should not have to check it again. It is second, and quieter, so the
              cautious path is the obvious one. */}
          <button
            onClick={handleImport}
            disabled={!file || importing || checking}
            className="flex items-center gap-2 rounded-xl border border-border px-4 py-2.5 text-[12px] font-mono uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
          >
            <Upload className="h-4 w-4" /> {importing ? "Importing…" : "Import for real"}
          </button>
        </div>

        {result && (
          <div className="mt-5">
            {/* A preview must never read like a receipt. Same numbers, different tense, different
                colour - somebody who skims this and walks away has to leave knowing whether their
                data is in. */}
            <div
              className={`mb-2 flex items-start gap-2 rounded-xl border px-3 py-2 text-sm ${
                isPreview
                  ? "border-blue-200 bg-blue-50 text-blue-900"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800"
              }`}
            >
              {isPreview ? (
                <Eye className="mt-0.5 h-4 w-4 shrink-0" />
              ) : (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              )}
              <div>
                <div className="font-medium">
                  {isPreview
                    ? total === 0
                      ? "Nothing new in this file — nothing has been imported"
                      : `This file would add ${total} record${total === 1 ? "" : "s"} — nothing has been imported yet`
                    : total === 0
                      ? "Nothing new to add"
                      : `Added ${total} record${total === 1 ? "" : "s"}`}
                </div>
                <div className="opacity-80">
                  {/* Only the row types this file actually touched. A sheet of nothing but
                      enrolments should not report "0 courses · 0 subjects · 0 instructors"
                      before the one number that matters. */}
                  {breakdown.join(" · ") || "nothing"}
                  {result.skipped_existing > 0 &&
                    ` · ${result.skipped_existing} already exist${isPreview ? "" : "ed"}`}
                </div>
                {isPreview && (
                  <button
                    onClick={handleImport}
                    disabled={importing}
                    className="mt-2 flex items-center gap-1.5 rounded-lg bg-primary px-2.5 py-1 text-[11px] font-mono uppercase tracking-wider text-white transition-colors hover:bg-primary/90 disabled:opacity-40"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    {importing ? "Importing…" : "Import this file"}
                  </button>
                )}
              </div>
            </div>

            {result.errors.length > 0 && (
              <div className="rounded-xl border border-orange-200 bg-orange-50 px-3 py-2 text-sm text-orange-800">
                <div className="mb-1 font-semibold">
                  {result.errors.length} row{result.errors.length === 1 ? "" : "s"}{" "}
                  {isPreview
                    ? "would be skipped — fix these in your sheet, or import anyway and the rest still lands"
                    : "skipped — everything else was imported"}
                </div>
                <ul className="list-inside list-disc space-y-0.5">
                  {result.errors.map((e, i) => (
                    <li key={i}>
                      Row {e.row}: {e.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
