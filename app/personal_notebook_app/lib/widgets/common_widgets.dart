import 'package:flutter/material.dart';

class ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  const ErrorView({super.key, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [
      const Icon(Icons.error_outline, size: 48, color: Colors.red),
      const SizedBox(height: 12),
      Text(message, textAlign: TextAlign.center, style: const TextStyle(color: Colors.red)),
      if (onRetry != null) ...[const SizedBox(height: 12), OutlinedButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh, size: 16), label: const Text('重试'))],
    ])),
  );
}

class LoadingView extends StatelessWidget {
  final String? message;
  const LoadingView({super.key, this.message});
  @override
  Widget build(BuildContext context) => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
    const CircularProgressIndicator(), const SizedBox(height: 12),
    Text(message ?? '加载中…', style: const TextStyle(color: Colors.grey)),
  ]));
}

class EmptyView extends StatelessWidget {
  final String message; final IconData icon; final Widget? action;
  const EmptyView({super.key, required this.message, this.icon = Icons.inbox, this.action});
  @override
  Widget build(BuildContext context) => Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [
    Icon(icon, size: 48, color: Colors.grey.shade300), const SizedBox(height: 12),
    Text(message, style: TextStyle(color: Colors.grey.shade500)),
    if (action != null) ...[const SizedBox(height: 12), action!],
  ])));
}

class StatusBadge extends StatelessWidget {
  final String status;
  const StatusBadge({super.key, required this.status});
  Color get _color => switch (status.toUpperCase()) {
    'READY' || 'SUCCESS' || 'COMPLETED' || 'OK' || 'RUNNING' => Colors.green,
    'FAILED' || 'ERROR' || 'CANCELLED' => Colors.red,
    'PENDING' || 'UPLOADED' || 'PARSING' || 'CHUNKING' || 'EMBEDDING' || 'INDEXING' || 'REINDEXING' => Colors.orange,
    _ => Colors.grey,
  };
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
    decoration: BoxDecoration(color: _color.withAlpha(30), borderRadius: BorderRadius.circular(12), border: Border.all(color: _color.withAlpha(100))),
    child: Text(status.toUpperCase(), style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: _color)),
  );
}

class JobStatusChip extends StatelessWidget {
  final String status; final String? phase; final double progress;
  const JobStatusChip({super.key, required this.status, this.phase, this.progress = 0});
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
    StatusBadge(status: status),
    if (phase != null) ...[const SizedBox(width: 4), Text(phase!, style: const TextStyle(fontSize: 11, color: Colors.grey))],
    if (progress > 0 && progress < 100) ...[const SizedBox(width: 4), Text('${progress.toInt()}%', style: const TextStyle(fontSize: 11))],
  ]);
}

class CitationCard extends StatelessWidget {
  final Map<String, dynamic> citation;
  const CitationCard({super.key, required this.citation});
  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.symmetric(vertical: 4),
    child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Expanded(child: Text(citation['filename'] ?? '', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
        Text('${((citation['score'] as num?) ?? 0 * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.primary)),
      ]),
      if (citation['section_path'] != null) Text(citation['section_path'], style: const TextStyle(fontSize: 11, color: Colors.grey)),
      const SizedBox(height: 4),
      Text(citation['content_preview'] ?? '', maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12)),
    ])),
  );
}

class RefusalBanner extends StatelessWidget {
  final String? reason;
  const RefusalBanner({super.key, this.reason});
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity, padding: const EdgeInsets.all(12),
    margin: const EdgeInsets.symmetric(vertical: 8),
    decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.orange.shade200)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Row(children: [Icon(Icons.warning_amber, size: 16, color: Colors.deepOrange), SizedBox(width: 4), Text('低置信度拒答', style: TextStyle(fontWeight: FontWeight.w600, color: Colors.deepOrange))]),
      if (reason != null) ...[const SizedBox(height: 4), Text(reason!, style: const TextStyle(fontSize: 12, color: Colors.deepOrange))],
    ]),
  );
}
