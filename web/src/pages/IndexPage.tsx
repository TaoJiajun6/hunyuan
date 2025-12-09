import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Mic, User } from 'lucide-react';
import { clsx } from 'clsx';

export default function IndexPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const tabs = [
    { id: 'podcast', label: 'AI播客', icon: Mic, path: '/podcast' },
    { id: 'mine', label: '我的', icon: User, path: '/mine' },
  ];

  const currentTab = tabs.find(tab => location.pathname.startsWith(tab.path))?.id || 'podcast';

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* 主内容区域 */}
      <div className="flex-1 overflow-hidden">
        <Outlet />
      </div>

      {/* 底部导航栏 */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div className="flex justify-around items-center h-16">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => navigate(tab.path)}
                className={clsx(
                  'flex flex-col items-center justify-center flex-1 h-full transition-colors',
                  isActive
                    ? 'text-primary-600 dark:text-primary-400'
                    : 'text-gray-500 dark:text-gray-400'
                )}
              >
                <Icon className="w-6 h-6 mb-1" />
                <span className="text-xs font-medium">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

