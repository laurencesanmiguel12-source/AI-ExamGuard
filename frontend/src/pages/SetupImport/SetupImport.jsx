import PageHeader from "../../components/PageHeader";
import SetupImportPanel from "../Dashboard/SetupImportPanel";

// Promoted out of the admin dashboard's tab strip and onto the sidebar, because it belongs with
// the three things it creates. Courses, Subjects and Instructors are each their own page under
// Academic Management; the bulk path to all three was the only one buried behind a dashboard tab,
// so the fastest way to set a school up was also the hardest to find.
//
// Moved rather than duplicated - a second door to the same screen makes it harder to describe
// where the feature lives, not easier to reach.
export default function SetupImport() {
  return (
    <div>
      <PageHeader
        eyebrow="Academic Management"
        title="Bulk Import"
        description="Set your school up from a spreadsheet instead of one form at a time. One CSV creates courses, subjects and instructors together, and rows refer to each other by code so a subject can name the course above it."
      />
      <SetupImportPanel />
    </div>
  );
}
