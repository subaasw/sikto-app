export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface SignupInput {
  name: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}
