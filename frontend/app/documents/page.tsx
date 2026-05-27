"use client";

import { useState } from "react";
import { Upload, FolderOpen, FileText, Trash2, RefreshCw, Eye } from "lucide-react";

export default function DocumentsPage() {
  const [kbId, setKbId] = useState("");
  const [documents] = useState<any[]>([]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">文档管理</h1>
        <p className="text-muted-foreground">导入和管理知识库文档</p>
      </div>

      {/* KB Selector & Import */}
      <div className="bg-card rounded-lg border p-4 space-y-4 max-w-lg">
        <input
          type="text"
          value={kbId}
          onChange={(e) => setKbId(e.target.value)}
          placeholder="知识库 ID"
          className="w-full px-3 py-2 border rounded-md text-sm bg-background"
        />
        <div className="flex flex-wrap gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm">
            <Upload className="h-4 w-4" /> 上传文件
          </button>
          <button className="flex items-center gap-2 px-4 py-2 border rounded-md text-sm hover:bg-accent">
            <FolderOpen className="h-4 w-4" /> 导入文件夹
          </button>
          <button className="flex items-center gap-2 px-4 py-2 border rounded-md text-sm hover:bg-accent">
            导入 NAS 路径
          </button>
        </div>
      </div>

      {/* Document List */}
      <div>
        <h3 className="font-semibold mb-3">文档列表</h3>
        {documents.length === 0 ? (
          <div className="text-center text-muted-foreground py-8 bg-card rounded-lg border">
            <FileText className="h-10 w-10 mx-auto mb-2 opacity-20" />
            <p className="text-sm">请先选择知识库，暂无文档</p>
          </div>
        ) : (
          <div className="bg-card rounded-lg border">
            <table className="w-full text-sm">
              <thead className="border-b">
                <tr className="text-left text-muted-foreground">
                  <th className="p-3">文件名</th>
                  <th className="p-3">类型</th>
                  <th className="p-3">大小</th>
                  <th className="p-3">状态</th>
                  <th className="p-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc: any) => (
                  <tr key={doc.id} className="border-b last:border-0 hover:bg-muted/50">
                    <td className="p-3 font-medium">{doc.filename}</td>
                    <td className="p-3">{doc.file_type}</td>
                    <td className="p-3">{doc.file_size}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        doc.parse_status === "completed" ? "bg-green-100 text-green-700"
                          : "bg-yellow-100 text-yellow-700"
                      }`}>
                        {doc.parse_status}
                      </span>
                    </td>
                    <td className="p-3 flex gap-2">
                      <button className="text-muted-foreground hover:text-foreground">
                        <Eye className="h-4 w-4" />
                      </button>
                      <button className="text-muted-foreground hover:text-foreground">
                        <RefreshCw className="h-4 w-4" />
                      </button>
                      <button className="text-red-400 hover:text-red-600">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
