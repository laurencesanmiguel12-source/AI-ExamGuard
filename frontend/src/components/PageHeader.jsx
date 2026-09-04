import SectionTag from "./ui/SectionTag";

/**
 * The standard way every screen introduces itself.
 *
 * Pages used to open with a section tag and a bare noun - "Courses", "Students", "Exams" - which
 * told you the name of the table below and nothing else: not which area of the system you were
 * in, not what the page was for, and on the dashboards not even which role's dashboard you were
 * looking at. Three parts fix that, and every screen now supplies all three:
 *
 *   eyebrow      which area of the system this belongs to (Academic Management, Proctoring, ...)
 *   title        what this screen IS, named as a module rather than a plural noun
 *   description  what you can actually do here, in one sentence
 *
 * `actions` keeps each page's primary button (Add Course, and so on) on the same row, which is
 * where they already sat.
 */
export default function PageHeader({ eyebrow, title, description, actions, children }) {
  return (
    <div className="mb-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <SectionTag text={eyebrow} />
          <h2 className="font-display font-black text-foreground text-4xl">{title}</h2>
          {description && (
            <p className="text-muted-foreground text-sm mt-2 max-w-2xl">{description}</p>
          )}
        </div>
        {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}
