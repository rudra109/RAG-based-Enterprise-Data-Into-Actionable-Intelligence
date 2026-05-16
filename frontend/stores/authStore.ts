import { create } from 'zustand';
import { User, onAuthStateChanged, signOut as firebaseSignOut } from 'firebase/auth';
import { auth } from '@/lib/firebase';

interface AuthState {
  user: User | null;
  loading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  signOut: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user }),
  setLoading: (loading) => set({ loading }),
  signOut: async () => {
    try {
      if (auth) {
        await firebaseSignOut(auth);
      }
      set({ user: null });
    } catch (error) {
      console.error('Error signing out:', error);
    }
  },
}));

// Initialize listener
if (typeof window !== 'undefined') {
  if (auth) {
    onAuthStateChanged(auth, (user) => {
      useAuth.getState().setUser(user);
      useAuth.getState().setLoading(false);
    });
  } else {
    useAuth.getState().setUser(null);
    useAuth.getState().setLoading(false);
  }
}
