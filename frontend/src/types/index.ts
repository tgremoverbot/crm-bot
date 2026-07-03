export interface AdminUser {
  id: string;
  email: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  default_sequence_id: string | null;
  created_at: string;
  updated_at: string;
}

export type MaterialKind =
  | 'text'
  | 'photo'
  | 'document'
  | 'video'
  | 'voice'
  | 'audio'
  | 'video_note'
  | 'animation'
  | 'sticker'
  | 'link';
export type ParseMode = 'MarkdownV2' | 'HTML' | 'none';

export interface Material {
  id: string;
  name: string;
  kind: MaterialKind;
  body: string | null;
  file_id: string | null;
  file_url: string | null;
  link_url: string | null;
  parse_mode: ParseMode;
  disable_web_page_preview: boolean;
  // Set only for messages captured via the bot's /admin mode — sent with
  // copy_message so they always match the original exactly.
  source_chat_id: number | null;
  source_message_id: number | null;
  created_at: string;
  updated_at: string;
}

export type TriggerKind = 'campaign_join' | 'manual' | 'tag_added';

export interface Sequence {
  id: string;
  name: string;
  description: string | null;
  trigger_kind: TriggerKind;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SequenceStep {
  id: string;
  sequence_id: string;
  position: number;
  delay_minutes: number;
  material_id: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  telegram_id: number;
  chat_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  language_code: string | null;
  is_blocked: boolean;
  source_campaign_id: string | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export type BroadcastStatus =
  | 'draft'
  | 'scheduled'
  | 'sending'
  | 'sent'
  | 'cancelled'
  | 'failed';

export interface Broadcast {
  id: string;
  name: string;
  material_id: string;
  segment_id: string | null;
  status: BroadcastStatus;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  recipient_count: number;
  success_count: number;
  failure_count: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface GrowthDay {
  date: string;
  new_users: number;
}

export interface InviteLinkFunnel {
  slug: string;
  name: string;
  joined: number;
  sequence_delivered: number;
}

export interface RecentBroadcast {
  id: string;
  name: string;
  status: string;
  recipient_count: number;
  success_count: number;
  failure_count: number;
  created_at: string;
}

export interface Stats {
  users: {
    total: number;
    new_today: number;
    new_this_week: number;
    new_prev_week: number;
    active_7d: number;
    blocked: number;
  };
  campaigns: { total: number; active: number };
  materials: { total: number };
  sequences: { total: number; active: number };
  broadcasts: { total: number; sent: number; recent: RecentBroadcast[] };
  messages: {
    delivered_total: number;
    delivered_this_week: number;
    delivered_prev_week: number;
  };
  scheduled: { pending: number };
  growth: { days: GrowthDay[]; window_days: number };
  funnels: { invite_links: InviteLinkFunnel[] };
  delivery: { sequence_success_rate: number | null };
}
