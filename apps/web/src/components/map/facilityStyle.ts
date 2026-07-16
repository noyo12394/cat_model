export function facilityColor(facilityType: string): string {
  switch (facilityType) {
    case "hospital":
      return "#d13b3b";
    case "fire_station":
      return "#d9761f";
    case "bridge":
    case "river_crossing":
      return "#1f6fd6";
    case "school":
      return "#1a8a4a";
    case "gauge":
      return "#0f9aa8";
    default:
      return "#6b7280";
  }
}

export function facilityIcon(facilityType: string): string {
  switch (facilityType) {
    case "hospital":
      return "H";
    case "fire_station":
      return "F";
    case "bridge":
    case "river_crossing":
      return "B";
    case "school":
      return "U";
    case "gauge":
      return "G";
    default:
      return "•";
  }
}

export function exposureColor(level: string): string {
  switch (level) {
    case "elevated":
      return "#d9761f";
    case "unavailable":
      return "#d13b3b";
    default:
      return "#1a8a4a";
  }
}
