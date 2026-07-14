export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border p-6">
          <p className="text-sm text-gray-500">经验总数</p>
          <p className="text-3xl font-bold mt-2">--</p>
        </div>
        <div className="rounded-lg border p-6">
          <p className="text-sm text-gray-500">经验复用率</p>
          <p className="text-3xl font-bold mt-2">--</p>
        </div>
        <div className="rounded-lg border p-6">
          <p className="text-sm text-gray-500">工作流成功率</p>
          <p className="text-3xl font-bold mt-2">--</p>
        </div>
        <div className="rounded-lg border p-6">
          <p className="text-sm text-gray-500">学习速度</p>
          <p className="text-3xl font-bold mt-2">--</p>
        </div>
      </div>
    </div>
  )
}
