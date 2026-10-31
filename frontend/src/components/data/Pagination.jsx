export function Pagination({ page, totalPages = 1 }) {
  return (
    <div>
      Page {page} of {totalPages}
    </div>
  );
}
