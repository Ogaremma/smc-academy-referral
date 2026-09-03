export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  photo_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer' | string;
  user: User;
  referral_code: string;
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
