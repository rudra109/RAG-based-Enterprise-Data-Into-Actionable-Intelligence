'use client';

import React, { Suspense, useState } from 'react';
import { Settings, User, Shield, Bell, Database, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import { useStore } from '@/store/useStore';

function normalizeTab(tab: string | null) {
  if (!tab) return 'Profile';
  return tab.charAt(0).toUpperCase() + tab.slice(1);
}

function SettingsPageContent() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => normalizeTab(searchParams.get('tab')));
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceType, setNewWorkspaceType] = useState('Team');
  const { selectedWorkspace, addWorkspace } = useStore();
  const isCreatingWorkspace = searchParams.get('mode') === 'create';

  const handleCreateWorkspace = (event: React.FormEvent) => {
    event.preventDefault();
    const name = newWorkspaceName.trim();

    if (!name) {
      toast.error('Workspace name is required');
      return;
    }

    addWorkspace({
      id: `workspace-${Date.now()}`,
      name,
      type: newWorkspaceType,
    });
    setNewWorkspaceName('');
    toast.success(`${name} workspace created`);
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'Profile':
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-white">General Configuration</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-slate-950 rounded-2xl border border-slate-800">
                <div>
                  <div className="text-sm font-bold text-white">Dark Mode</div>
                  <div className="text-xs text-slate-500">Enable high-contrast dark interface</div>
                </div>
                <div className="w-12 h-6 bg-indigo-600 rounded-full relative p-1 cursor-pointer">
                  <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-md" />
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-950 rounded-2xl border border-slate-800">
                <div>
                  <div className="text-sm font-bold text-white">Auto-refresh</div>
                  <div className="text-xs text-slate-500">Automatically update dashboards every 30s</div>
                </div>
                <div className="w-12 h-6 bg-indigo-600 rounded-full relative p-1 cursor-pointer">
                  <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-md" />
                </div>
              </div>
            </div>
          </div>
        );
      case 'Workspace':
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-white">Workspace Configuration</h2>
            {isCreatingWorkspace && (
              <form onSubmit={handleCreateWorkspace} className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-5 space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-white">Create Workspace</h3>
                  <p className="text-xs text-slate-500 mt-1">Add a separate area for team data, dashboards, pipelines, and anomalies.</p>
                </div>
                <div className="grid gap-4 md:grid-cols-[1fr_180px_auto] md:items-end">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-400">New Workspace Name</label>
                    <input
                      type="text"
                      value={newWorkspaceName}
                      onChange={(event) => setNewWorkspaceName(event.target.value)}
                      placeholder="e.g. Finance Ops"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-400">Type</label>
                    <select
                      value={newWorkspaceType}
                      onChange={(event) => setNewWorkspaceType(event.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none"
                    >
                      <option>Team</option>
                      <option>Department</option>
                      <option>Client</option>
                      <option>Sandbox</option>
                    </select>
                  </div>
                  <Button type="submit" className="bg-indigo-600 hover:bg-indigo-500 text-white">
                    Create
                  </Button>
                </div>
              </form>
            )}
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-400">Workspace Name</label>
                <input 
                  type="text" 
                  defaultValue={selectedWorkspace}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-400">Data Retention (Days)</label>
                <select className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:border-indigo-500 outline-none">
                  <option>30 Days</option>
                  <option>60 Days</option>
                  <option>90 Days</option>
                  <option>Unlimited</option>
                </select>
              </div>
            </div>
          </div>
        );
      case 'Security':
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-white">Security & Access</h2>
            <div className="space-y-4">
              <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold text-white">Two-Factor Authentication</div>
                  <div className="text-xs text-slate-500">Add an extra layer of security to your account</div>
                </div>
                <div className="w-12 h-6 bg-slate-800 rounded-full relative p-1 cursor-pointer">
                  <div className="absolute left-1 top-1 w-4 h-4 bg-slate-400 rounded-full shadow-md" />
                </div>
              </div>
              <div className="pt-4">
                <Button variant="outline" className="border-slate-800 text-slate-300 hover:bg-slate-800">
                  Change Password
                </Button>
              </div>
            </div>
          </div>
        );
      case 'Notifications':
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-white">Notification Preferences</h2>
            <div className="space-y-4">
              {['Email Alerts', 'System Notifications', 'Weekly Reports'].map((item) => (
                <div key={item} className="flex items-center justify-between p-4 bg-slate-950 rounded-2xl border border-slate-800">
                  <div className="text-sm font-bold text-white">{item}</div>
                  <div className="w-12 h-6 bg-indigo-600 rounded-full relative p-1 cursor-pointer">
                    <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full shadow-md" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      case 'Integrations':
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-white">Connected Services</h2>
            <div className="grid grid-cols-1 gap-4">
              {[
                { name: 'Slack', status: 'Connected', desc: 'Receive anomaly alerts in Slack channels' },
                { name: 'GitHub', status: 'Not Connected', desc: 'Sync technical documentation repositories' },
                { name: 'Jira', status: 'Connected', desc: 'Automate ticket creation for system failures' }
              ].map((service) => (
                <div key={service.name} className="flex items-center justify-between p-4 bg-slate-950 rounded-2xl border border-slate-800">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center font-bold text-slate-400">
                      {service.name[0]}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-white">{service.name}</div>
                      <div className="text-xs text-slate-500">{service.desc}</div>
                    </div>
                  </div>
                  <Button 
                    variant={service.status === 'Connected' ? 'outline' : 'default'}
                    className={service.status === 'Connected' ? 'border-slate-800 text-slate-400' : 'bg-indigo-600 text-white'}
                  >
                    {service.status === 'Connected' ? 'Disconnect' : 'Connect'}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-700 bg-[#020617] min-h-screen text-slate-200">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <Settings className="w-8 h-8 text-slate-500" />
          System Settings
        </h1>
        <p className="text-slate-500 mt-2">Manage your workspace configuration and personal preferences.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="space-y-2">
          <SettingsTab 
            icon={<User className="w-4 h-4" />} 
            label="Profile" 
            active={activeTab === 'Profile'} 
            onClick={() => setActiveTab('Profile')}
          />
          <SettingsTab 
            icon={<Database className="w-4 h-4" />} 
            label="Workspace" 
            active={activeTab === 'Workspace'}
            onClick={() => setActiveTab('Workspace')}
          />
          <SettingsTab 
            icon={<Shield className="w-4 h-4" />} 
            label="Security" 
            active={activeTab === 'Security'}
            onClick={() => setActiveTab('Security')}
          />
          <SettingsTab 
            icon={<Bell className="w-4 h-4" />} 
            label="Notifications" 
            active={activeTab === 'Notifications'}
            onClick={() => setActiveTab('Notifications')}
          />
          <SettingsTab 
            icon={<Globe className="w-4 h-4" />} 
            label="Integrations" 
            active={activeTab === 'Integrations'}
            onClick={() => setActiveTab('Integrations')}
          />
        </div>

        <div className="md:col-span-2 space-y-8">
          <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 space-y-6 shadow-2xl">
            {renderContent()}

            <div className="pt-4 flex gap-3">
              <Button 
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-8"
                onClick={() => toast.success('Settings saved successfully')}
              >
                Save Changes
              </Button>
              <Button variant="ghost" className="text-slate-500 hover:text-white">Reset to Default</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-slate-500">Loading settings...</div>}>
      <SettingsPageContent />
    </Suspense>
  );
}

function SettingsTab({ icon, label, active, onClick }: any) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
        active ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 shadow-lg' : 'text-slate-500 hover:bg-slate-900 hover:text-slate-300'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
