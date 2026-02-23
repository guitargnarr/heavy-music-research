import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";

interface ScoreRadarProps {
  trajectory: number;
  industrySignal: number;
  engagement: number;
  releasePositioning: number;
}

export function ScoreRadar({
  trajectory,
  industrySignal,
  engagement,
  releasePositioning,
}: ScoreRadarProps) {
  const data = [
    { dim: "Trajectory", value: trajectory },
    { dim: "Industry", value: industrySignal },
    { dim: "Engagement", value: engagement },
    { dim: "Release", value: releasePositioning },
  ];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="#333" />
        <PolarAngleAxis
          dataKey="dim"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
        />
        <Radar
          dataKey="value"
          stroke="#dc2626"
          fill="#dc2626"
          fillOpacity={0.15}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
