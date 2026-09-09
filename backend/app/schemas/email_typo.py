"""Catches a mistyped domain on a well-known email provider.

**This is not general email validation - that already exists and already works.** Every schema
that takes an address uses pydantic's `EmailStr`, backed by `email-validator`, and it correctly
rejects malformed input like `not-an-email` or `a@b`.

What it cannot reject is `jrizal@gmail.cmo`, found in live production data. That address is
perfectly valid RFC syntax: `.cmo` is a plausible top-level domain as far as any format check is
concerned. No amount of syntax validation catches it, and the consequence is quiet and permanent -
the account can never receive a password reset or any notification, and nobody discovers this
until someone needs it to work.

So this is a deliberately narrow guard, the same one real signup forms use: if the domain is one
small typo away from a provider people actually use, say so and name the correction. An unknown
domain is left completely alone - `arellano.edu.ph` or any school's own mail domain must pass
untouched, so this can never become a gatekeeper on legitimate addresses it has never heard of.
"""

# Only providers common enough that a near-miss is far more likely to be a typo than a real
# domain. Deliberately short: every entry added here is a chance to reject something legitimate.
KNOWN_PROVIDERS = (
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
)


def _edit_distance_at_most(a: str, b: str, limit: int) -> bool:
    """Damerau-Levenshtein (optimal string alignment) distance <= limit.

    Transposition has to count as ONE edit, not two, and that is the whole reason this is not
    plain Levenshtein: the address that prompted this, `gmail.cmo`, is `gmail.com` with the last
    two characters swapped. Plain Levenshtein scores that as two substitutions, so a distance-1
    check silently misses the single most common class of typo there is - which is exactly what
    happened on the first attempt at this function.

    Hand-rolled rather than adding a dependency for one small check, matching the codebase's
    minimal-dependency convention.
    """
    if abs(len(a) - len(b)) > limit:
        return False
    if a == b:
        return True

    rows, cols = len(a) + 1, len(b) + 1
    d = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        d[i][0] = i
    for j in range(cols):
        d[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,        # deletion
                d[i][j - 1] + 1,        # insertion
                d[i - 1][j - 1] + cost,  # substitution
            )
            # Transposition of two adjacent characters - one edit, not two.
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
        if min(d[i]) > limit:
            return False

    return d[-1][-1] <= limit


def suggest_domain_correction(email: str) -> str | None:
    """The provider this address was probably meant to use, or None if it looks fine.

    Returns None for an exact match on a known provider and for any domain not resembling one, so
    the overwhelming majority of addresses - including every institutional domain - pass straight
    through.
    """
    if not email or "@" not in email:
        return None

    domain = email.rsplit("@", 1)[1].strip().lower()
    if not domain or domain in KNOWN_PROVIDERS:
        return None

    for provider in KNOWN_PROVIDERS:
        # One edit covers the realistic slips: gmail.cmo, gmail.con, gmial.com, gmail.co.
        if _edit_distance_at_most(domain, provider, 1):
            return provider
    return None


def check_email_typo(email: str) -> None:
    """Raises ValueError naming the correction, for use as a pydantic field validator."""
    suggestion = suggest_domain_correction(email)
    if suggestion is not None:
        raise ValueError(
            f"'{email}' looks like a typo - did you mean @{suggestion}? "
            f"An address with a mistyped domain can never receive a password reset."
        )
