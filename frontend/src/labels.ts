// Plain-language labels for a non-technical news reader audience.
// Keeps the underlying technical values from the API but shows
// friendly text in the UI.

export const POOL_LABELS: Record<string, string> = {
  western_mainstream: 'Western media',
  russian_state: 'Russian state media',
  russian_independent: 'Russian independent',
  chinese_state: 'Chinese state media',
  neutral_wire: 'Wire services',
  middle_eastern: 'Middle East',
  latin_american: 'Latin America',
  african: 'Africa',
  south_asian: 'South Asia',
  east_asian: 'East Asia',
};

// Short labels for compact UI (badges, dots)
export const POOL_LABELS_SHORT: Record<string, string> = {
  western_mainstream: 'Western',
  russian_state: 'Russian state',
  russian_independent: 'Russian ind.',
  chinese_state: 'Chinese state',
  neutral_wire: 'Wire',
  middle_eastern: 'Middle East',
  latin_american: 'Latin America',
  african: 'Africa',
  south_asian: 'South Asia',
  east_asian: 'East Asia',
};

export const POOL_ORDER = [
  'western_mainstream',
  'russian_state',
  'russian_independent',
  'chinese_state',
  'neutral_wire',
  'middle_eastern',
  'latin_american',
  'african',
  'south_asian',
  'east_asian',
];

export function poolLabel(pool: string): string {
  return POOL_LABELS[pool] || pool;
}

export function poolLabelShort(pool: string): string {
  return POOL_LABELS_SHORT[pool] || pool;
}

// Plain-language reliability labels (was: confidence class)
export const RELIABILITY_LABELS: Record<string, string> = {
  confirmed: 'Confirmed',
  probable: 'Likely true',
  single_source: 'One source only',
  disputed: 'Conflicting reports',
  unknown: 'Unverified',
};

export function reliabilityLabel(value: string): string {
  return RELIABILITY_LABELS[value] || value;
}

// Reliability badge color class
export function reliabilityBadgeClass(value: string): string {
  switch (value) {
    case 'confirmed':
      return 'badge-green';
    case 'probable':
      return 'badge-blue';
    case 'disputed':
      return 'badge-yellow';
    case 'single_source':
    case 'unknown':
    default:
      return 'badge-gray';
  }
}

// Plain-language claim type labels (was: claim bucket)
export const CLAIM_TYPE_LABELS: Record<string, string> = {
  verified_fact: 'Fact',
  attributed_statement: 'Quote',
  inference: 'Analysis',
  opinionated_framing: 'Opinion',
};

export function claimTypeLabel(bucket: string): string {
  return CLAIM_TYPE_LABELS[bucket] || bucket.replace(/_/g, ' ');
}

// Plain-language bias signal labels (was: propaganda flags)
export const BIAS_SIGNAL_LABELS: Record<string, { label: string; desc: string }> = {
  loaded_language: {
    label: 'Emotional language',
    desc: 'Words chosen to provoke a strong reaction rather than describe facts.',
  },
  us_vs_them: {
    label: 'Us-vs-them framing',
    desc: 'Presents the story as a conflict between opposing sides rather than reporting events.',
  },
  certainty_without_evidence: {
    label: 'Claims without proof',
    desc: 'Strong assertions stated as fact without supporting evidence.',
  },
};

export function biasSignalLabel(flag: string): { label: string; desc: string } {
  return BIAS_SIGNAL_LABELS[flag] || { label: flag.replace(/_/g, ' '), desc: '' };
}

// Plain-language agreement labels (was: agreement_level)
export const AGREEMENT_LABELS: Record<string, string> = {
  agreed: 'All sources agree',
  variant: 'Minor differences',
  disputed: 'Conflicting accounts',
  single_source: 'Reported by one source',
};

export function agreementLabel(level: string): string {
  return AGREEMENT_LABELS[level] || level;
}

// Plain-language field labels (was: raw field names like event_type)
export const FIELD_LABELS: Record<string, string> = {
  actor: 'Who did it?',
  weapon_type: 'What was used?',
  location: 'Where?',
  casualties: 'Casualties',
  target: 'What was affected?',
  event_type: 'Type of event',
  time: 'When?',
};

export function fieldLabel(field: string): string {
  return FIELD_LABELS[field] || field.replace(/_/g, ' ');
}

// Pool colors (also mirrored in App.css .pool-dot.* for the dots)
export function poolColor(pool: string): string {
  switch (pool) {
    case 'western_mainstream':
      return '#60a5fa';
    case 'russian_state':
      return '#f87171';
    case 'russian_independent':
      return '#a78bfa';
    case 'chinese_state':
      return '#fb923c';
    case 'neutral_wire':
      return '#34d399';
    case 'middle_eastern':
      return '#fbbf24';
    case 'latin_american':
      return '#22d3ee';
    case 'african':
      return '#f97316';
    case 'south_asian':
      return '#818cf8';
    case 'east_asian':
      return '#fb7185';
    default:
      return '#6b7280';
  }
}

export function poolIcon(pool: string): string {
  switch (pool) {
    case 'western_mainstream':
      return '🌍';
    case 'russian_state':
      return '🇷🇺';
    case 'russian_independent':
      return '🗣️';
    case 'chinese_state':
      return '🇨🇳';
    case 'neutral_wire':
      return '📡';
    case 'middle_eastern':
      return '🕌';
    case 'latin_american':
      return '🌎';
    case 'african':
      return '🌍';
    case 'south_asian':
      return '🛕';
    case 'east_asian':
      return '⛩️';
    default:
      return '📰';
  }
}
