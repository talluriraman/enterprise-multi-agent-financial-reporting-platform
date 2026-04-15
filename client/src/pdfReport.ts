import { jsPDF } from "jspdf";

/** Plain-text financial report as a downloadable PDF (no JSON). */
export function downloadReportPdf(body: string, requestId?: string | null): void {
  const plain = body
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .trim();

  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const margin = 48;
  const maxW = pageW - margin * 2;
  let y = margin;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text("Enterprise Multi-Agent Financial Report", margin, y);
  y += 22;
  if (requestId) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(80, 80, 80);
    doc.text(`Request ID: ${requestId}`, margin, y);
    y += 16;
    doc.setTextColor(0, 0, 0);
  }
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);

  const lines = doc.splitTextToSize(plain, maxW);
  const lineH = 13;
  for (const line of lines) {
    if (y > pageH - margin) {
      doc.addPage();
      y = margin;
    }
    doc.text(line, margin, y);
    y += lineH;
  }

  const suffix = requestId ? `-${String(requestId).slice(0, 8)}` : "";
  doc.save(`financial-report${suffix}.pdf`);
}
