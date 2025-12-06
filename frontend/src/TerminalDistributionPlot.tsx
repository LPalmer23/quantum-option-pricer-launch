import Plot from "react-plotly.js";

type HistogramBin = {
  k: number;
  S: number;
  prob: number;
};

type Props = {
  histogram: HistogramBin[];
};

export default function TerminalDistributionPlot({ histogram }: Props) {
  const x = histogram.map((b) => b.S);
  const y = histogram.map((b) => b.prob);

  const data = [
    {
      x,
      y,
      type: "bar" as const,
      marker: {
        color: "#38bdf8",
      },
    },
  ];

  const layout = {
    title: {
      text: "Quantum Terminal Price Distribution",
      font: { size: 18, color: "#e5e7eb" },
    },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    xaxis: {
      title: "Terminal Price (Sₖ)",
      color: "#e5e7eb",
    },
    yaxis: {
      title: "Probability",
      color: "#e5e7eb",
    },
    margin: { t: 40, l: 50, r: 20, b: 50 },
  };

  const config = {
    displaylogo: false, // hide Plotly logo
    scrollZoom: true,   // keep scroll-to-zoom
    responsive: true,
  };

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <Plot
        data={data as any}
        layout={layout as any}
        config={config as any}
        style={{ width: "100%", height: "360px" }}
      />
    </div>
  );
}
