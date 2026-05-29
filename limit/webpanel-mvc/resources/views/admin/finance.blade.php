@extends('layouts.app')

@section('content')
<div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h2 class="mb-0 fw-bold text-dark">Dashboard Keuangan</h2>
            <p class="text-secondary">Statistik pendapatan dan histori transaksi keseluruhan.</p>
        </div>
        <div>
            <form action="{{ route('admin.finance') }}" method="GET" class="d-flex gap-2">
                <select name="filter" class="form-select border-secondary shadow-sm" onchange="this.form.submit()">
                    <option value="all" {{ $filter == 'all' ? 'selected' : '' }}>Semua Waktu</option>
                    <option value="harian" {{ $filter == 'harian' ? 'selected' : '' }}>Hari Ini</option>
                    <option value="mingguan" {{ $filter == 'mingguan' ? 'selected' : '' }}>Minggu Ini</option>
                    <option value="bulanan" {{ $filter == 'bulanan' ? 'selected' : '' }}>Bulan Ini</option>
                </select>
            </form>
        </div>
    </div>

    <!-- Statistik Total -->
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card bg-success text-white border-0 shadow-sm lift-hover">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <div class="text-white-50 small mb-1">Total Pendapatan (Sukses)</div>
                            <h3 class="mb-0 fw-bold">Rp {{ number_format($totalPendapatan, 0, ',', '.') }}</h3>
                        </div>
                        <div class="fs-1 text-white-50 opacity-50">
                            <i class="fas fa-money-bill-wave"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <!-- Royal Customers -->
        <div class="col-md-5 mb-4">
            <div class="card border-0 shadow-sm h-100">
                <div class="card-header bg-white border-bottom">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-crown text-warning me-2"></i>Pelanggan Royal (Top 10)</h5>
                </div>
                <div class="card-body p-0">
                    <ul class="list-group list-group-flush">
                        @forelse($royalCustomers as $idx => $royal)
                        <li class="list-group-item d-flex justify-content-between align-items-center py-3">
                            <div class="d-flex align-items-center gap-3">
                                <span class="badge {{ $idx < 3 ? 'bg-warning text-dark' : 'bg-secondary' }} rounded-pill">{{ $idx + 1 }}</span>
                                <div>
                                    <div class="fw-bold text-dark">{{ $royal->name }}</div>
                                    <div class="small text-secondary">{{ $royal->username }}</div>
                                </div>
                            </div>
                            <div class="text-success fw-bold">Rp {{ number_format($royal->transactions_sum_total_amount, 0, ',', '.') }}</div>
                        </li>
                        @empty
                        <li class="list-group-item text-center text-muted py-4">Belum ada pelanggan.</li>
                        @endforelse
                    </ul>
                </div>
            </div>
        </div>

        <!-- Transaksi Terkini -->
        <div class="col-md-7 mb-4">
            <div class="card border-0 shadow-sm h-100">
                <div class="card-header bg-white border-bottom d-flex justify-content-between align-items-center">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-history text-info me-2"></i>Transaksi Terkini</h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="px-3">Waktu</th>
                                    <th class="px-3">User</th>
                                    <th class="px-3">Tipe</th>
                                    <th class="px-3">Nominal</th>
                                    <th class="px-3">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                @forelse($recentTransactions as $trx)
                                <tr>
                                    <td class="px-3 text-secondary small">{{ $trx->created_at->format('d M Y H:i') }}</td>
                                    <td class="px-3 fw-bold text-dark">{{ $trx->user->username ?? 'Unknown' }}</td>
                                    <td class="px-3">
                                        @if($trx->type == 'topup')
                                        <span class="badge bg-info">Top Up</span>
                                        @else
                                        <span class="badge bg-primary">Beli VPN</span>
                                        @endif
                                    </td>
                                    <td class="px-3 fw-bold text-dark">Rp {{ number_format($trx->total_amount, 0, ',', '.') }}</td>
                                    <td class="px-3">
                                        @if($trx->status == 'success')
                                        <span class="badge bg-success">Sukses</span>
                                        @elseif($trx->status == 'pending')
                                        <span class="badge bg-warning text-dark">Pending</span>
                                        @else
                                        <span class="badge bg-danger">{{ ucfirst($trx->status) }}</span>
                                        @endif
                                    </td>
                                </tr>
                                @empty
                                <tr>
                                    <td colspan="5" class="text-center text-muted py-4">Belum ada transaksi.</td>
                                </tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                </div>
                @if($recentTransactions->hasPages())
                <div class="card-footer bg-white border-top">
                    {{ $recentTransactions->links() }}
                </div>
                @endif
            </div>
        </div>
    </div>
</div>
@endsection
