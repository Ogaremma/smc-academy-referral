export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  photo_url: string | null;
  is_active: boolean;
  account_status?: string;
  is_admin?: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer' | string;
  user: User | null;
  referral_code: string | null;
  affiliate_active?: boolean;
}

export interface UserProfileResponse {
  user: User;
  referral_code: string;
}

export interface ReferralActivity {
  id: number;
  status: string;
  verified_at: string | null;
}

export interface DashboardResponse {
  total_verified_referrals: number;
  pending_referrals: number;
  personal_referral_link: string;
  registration_form_url: string | null;
  recent_verified_activity: ReferralActivity[];
}

export interface DashboardData {
  profile: UserProfileResponse;
  dashboard: DashboardResponse;
}

export interface ReferralSummary {
  id: number;
  name: string;
  email: string | null;
  telegram: string | null;
  course: string | null;
  status: string;
  created_at: string;
  registered_at: string | null;
  verified_at: string | null;
}

export interface ReferralDetail extends ReferralSummary {
  form_fields: SubmissionField[];
}

export interface ReferralsResponse {
  total: number;
  registered: number;
  referrals: ReferralSummary[];
}

export interface PayoutDetails {
  account_name: string;
  bank_name: string;
  account_number: string;
  updated_at: string;
}

export interface PayoutInput {
  account_name: string;
  bank_name: string;
  account_number: string;
}

export type AdminPayout = PayoutDetails;

export interface AdminUserSummary {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  photo_url: string | null;
}

export interface AdminUser extends AdminUserSummary {
  account_status: string;
  is_admin: boolean;
  is_protected_admin: boolean;
  created_at: string;
}

export interface AdminAffiliate extends AdminUser {
  account_status: 'ACTIVE' | 'REVOKED';
  referral_code: string;
  referral_count: number;
}

export interface AdminAffiliateDetail extends AdminAffiliate {
  is_active: boolean;
}

export interface SubmissionField {
  label: string;
  value: string;
  category: 'registration' | 'payment' | string;
  is_link: boolean;
}

export interface AdminReferral {
  id: number;
  referrer: AdminUserSummary;
  referral_code: string | null;
  candidate_email: string | null;
  candidate_telegram_handle: string | null;
  status: 'verified' | 'pending' | 'rejected' | string;
  created_at: string;
  registered_at: string | null;
  verified_at: string | null;
  payment_proof_url?: string | null;
  form_fields?: SubmissionField[];
}

export interface AdminAuditLog {
  id: number;
  action: string;
  actor: AdminUserSummary;
  target: AdminUserSummary | null;
  metadata_json: string | null;
  created_at: string;
}

export interface AdminBroadcast {
  id: number;
  actor: AdminUserSummary;
  message: string;
  status: 'QUEUED' | 'SENDING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | string;
  target_count: number;
  success_count: number;
  failed_count: number;
  created_at: string;
  completed_at: string | null;
}
