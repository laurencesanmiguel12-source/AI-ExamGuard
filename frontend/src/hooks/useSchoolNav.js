import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getSchoolBySlug } from "../api/schools";

export function useSchoolSlug() {
  return useParams().schoolSlug;
}

// Drop-in replacement for useNavigate() that prefixes school-scoped paths with the
// current URL's school slug, e.g. navigate("/dashboard") -> "/arellano-university/dashboard".
export function useSchoolNav() {
  const navigate = useNavigate();
  const schoolSlug = useSchoolSlug();
  return (path, opts) => navigate(`/${schoolSlug}${path}`, opts);
}

// Resolves the current URL's school slug to the full school record (for display, e.g.
// showing the university name on the login page). Bounces to "/" if the slug is unknown.
export function useSchool() {
  const schoolSlug = useSchoolSlug();
  const navigate = useNavigate();
  const [school, setSchool] = useState(null);

  useEffect(() => {
    let active = true;
    getSchoolBySlug(schoolSlug).then((found) => {
      if (!active) return;
      if (!found) navigate("/", { replace: true });
      else setSchool(found);
    });
    return () => {
      active = false;
    };
  }, [schoolSlug]);

  return school;
}
