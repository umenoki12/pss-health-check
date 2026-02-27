import { useState, useEffect } from 'react'

const STATUS_PRIORITY = {
  'ABNORMAL': 1,
  'OFFLINE': 2,
  'NORMAL': 3,
}

function App() {
  const [computers, setComputers] = useState([])
  const [error, setError] = useState(null)

  // ステータス判定
  const getPCStatus = (pc) => {
    const now = new Date()
    const lastSeenDate = new Date(pc.last_seen)
    if ((now - lastSeenDate) > 5 * 60 * 1000) return 'OFFLINE'

    const isCpuHigh = pc.cpu_percent > 90
    const isMemHigh = pc.memory_percent > 90
    
    let isDiskHigh = false
    if (pc.disk_partitions) {
      isDiskHigh = Object.values(pc.disk_partitions).some(usage => usage > 90)
    }

    let targetError = false
    if (pc.targets_status) {
      targetError = Object.values(pc.targets_status).some(status => status === false)
    }

    if (isCpuHigh || isMemHigh || isDiskHigh || targetError) return 'ABNORMAL'
    return 'NORMAL'
  }

  // ソート機能
  const sortComputers = (data) => {
    return data.sort((a, b) => {
      const statusA = getPCStatus(a)
      const statusB = getPCStatus(b)
      if (STATUS_PRIORITY[statusA] !== STATUS_PRIORITY[statusB]) {
        return STATUS_PRIORITY[statusA] - STATUS_PRIORITY[statusB]
      }
      return a.id.localeCompare(b.id)
    })
  }

  // ★追加: 削除機能
// ★追加・修正: 削除機能（パスワード認証付き）
  const handleDelete = async (id) => {
    // 1. まず本当に削除するか確認
    if (!window.confirm(`本当にPC「${id}」を削除してもよろしいですか？\n(データは完全に消えます)`)) {
      return;
    }

    // 2. ★追加: 管理者パスワードを入力させるポップアップを出す
    const token = prompt("管理者のパスワードを入力してください:");
    
    // キャンセルされたり、空欄だった場合はここで処理を止める
    if (!token) {
      alert("パスワードが入力されなかったため、削除をキャンセルしました。");
      return;
    }

    try {
      // 3. ★修正: fetchの際に、入力されたパスワードをヘッダーに乗せて送る
      const response = await fetch(`http://127.0.0.1:5000/api/computers/${id}`, {
        method: 'DELETE',
        headers: {
          'X-Admin-Token': token  // これがバックエンドの check_admin_auth() に届きます！
        }
      });

      // 4. ★修正: バックエンドからの返事（ステータスコード）によって処理を分ける
      if (response.ok) {
        // 成功 (200 OK)
        setComputers(prev => prev.filter(pc => pc.id !== id));
        alert(`PC「${id}」を正常に削除しました。`);
      } else if (response.status === 401) {
        // パスワード間違い (401 Unauthorized)
        alert("❌ パスワードが間違っています。削除できません。");
      } else {
        // その他のエラー
        alert("削除に失敗しました。サーバーエラーです。");
      }
    } catch (err) {
      console.error(err);
      alert("削除できませんでした。バックエンドとの通信を確認してください。");
    }
  }

  const fetchComputers = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/computers')
      if (!response.ok) throw new Error(response.statusText)
      let data = await response.json()
      data = sortComputers(data)
      setComputers(data)
    } catch (err) {
      console.error("Fetch error:", err)
      setError("データの取得に失敗しました。")
    }
  }

  useEffect(() => {
    fetchComputers()
    const interval = setInterval(fetchComputers, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', backgroundColor: '#eee', minHeight: '100vh', color: '#333' }}>
      <h1 style={{ margin: '0 0 20px 0' }}>PSS ヘルスチェック管理者画面</h1>
      {error && <div style={{ color: 'red' }}>{error}</div>}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', justifyContent: 'flex-start' }}>
        {computers.map((pc) => (
          <PC_Card 
            key={pc.id} 
            pc={pc} 
            status={getPCStatus(pc)} 
            onDelete={handleDelete} // ★削除関数を渡す
          />
        ))}
      </div>
    </div>
  )
}

function PC_Card({ pc, status, onDelete }) {
  let bgColor = '#d4edda'
  let statusText = '🟢 NORMAL'
  let statusColor = 'green'
  
  if (status === 'OFFLINE') {
    bgColor = '#d6d8db'
    statusText = '🔴 OFFLINE'
    statusColor = '#555'
  } else if (status === 'ABNORMAL') {
    bgColor = '#f8d7da'
    statusText = '🟡 ABNORMAL'
    statusColor = '#721c24'
  }

  const isCpuHigh = pc.cpu_percent > 90
  const isMemHigh = pc.memory_percent > 90

  return (
    <div style={{ 
      border: '1px solid rgba(0,0,0,.125)', 
      borderRadius: '8px', 
      padding: '20px', 
      width: '350px',
      backgroundColor: bgColor,
      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
      color: '#333',
      position: 'relative' // 削除ボタンの配置用
    }}>
      {/* ★追加: 削除ボタン (右上に配置) */}
      <button 
        onClick={() => onDelete(pc.id)}
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'rgba(255,255,255,0.5)',
          border: '1px solid #ccc',
          borderRadius: '4px',
          cursor: 'pointer',
          padding: '2px 8px',
          fontSize: '12px'
        }}
        title="このPCを削除"
      >
        🗑️ 削除
      </button>

      <h2 style={{ margin: '0 0 10px 0', fontSize: '1.3em', paddingRight: '40px' }}>{pc.id}</h2>
      <div style={{ fontWeight: 'bold', marginBottom: '15px', fontSize: '1.1em', color: statusColor }}>
        {statusText}
      </div>

      <div style={{ marginBottom: '15px' }}>
        <div>CPU: <span style={{ color: isCpuHigh ? '#d9534f' : 'inherit', fontWeight: isCpuHigh ? 'bold' : 'normal' }}>{pc.cpu_percent?.toFixed(1)}%</span></div>
        <div>MEM: <span style={{ color: isMemHigh ? '#d9534f' : 'inherit', fontWeight: isMemHigh ? 'bold' : 'normal' }}>{pc.memory_percent?.toFixed(1)}%</span></div>
        
        <div style={{ marginTop: '5px', paddingTop: '5px', borderTop: '1px dashed #ccc' }}>
            <span style={{ fontSize: '0.9em', fontWeight: 'bold' }}>Storage:</span>
            {pc.disk_partitions && Object.keys(pc.disk_partitions).length > 0 ? (
                Object.entries(pc.disk_partitions).map(([diskName, usage]) => (
                    <div key={diskName} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9em', marginLeft: '10px' }}>
                        <span>{diskName}</span>
                        <span style={{ 
                            color: usage > 90 ? '#d9534f' : 'inherit', 
                            fontWeight: usage > 90 ? 'bold' : 'normal' 
                        }}>
                            {usage}%
                        </span>
                    </div>
                ))
            ) : (
                <span style={{ fontSize: '0.8em', color: '#666', marginLeft: '5px' }}>情報なし</span>
            )}
        </div>
      </div>

      <div style={{ background: 'rgba(255,255,255,0.6)', padding: '10px', borderRadius: '4px', fontSize: '0.9em' }}>
        <strong>監視プロセス:</strong>
        {pc.targets_status && Object.keys(pc.targets_status).length > 0 ? (
           Object.entries(pc.targets_status).map(([name, isRunning]) => (
             <div key={name} style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px', borderBottom: '1px dotted #ccc' }}>
               <span style={{ marginRight: '10px', wordBreak: 'break-all' }}>{name}</span>
               <span style={{ fontWeight: 'bold', color: isRunning ? 'green' : '#d9534f' }}>
                 {isRunning ? 'Running' : 'STOPPED'}
               </span>
             </div>
           ))
        ) : (
          <div style={{ color: '#666' }}>なし</div>
        )}
      </div>

      <div style={{ fontSize: '0.8em', color: '#555', marginTop: '15px', textAlign: 'right' }}>
        最終通信: {new Date(pc.last_seen).toLocaleString()}
      </div>
    </div>
  )
}

export default App