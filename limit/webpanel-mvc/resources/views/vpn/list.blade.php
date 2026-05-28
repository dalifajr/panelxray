@extends('layouts.app')

@section('content')
<div class="container py-4">
    <div class="row mb-4 align-items-center">
        <div class="col-md-6">
            <h2 class="fw-bold mb-0 text-uppercase">Daftar Akun {{ strtoupper($protocol) }}</h2>
        </div>
        <div class="col-md-6 text-end">
            <a href="{{ route('vpn.create', $protocol) }}" class="btn btn-primary">
                <i class="fas fa-plus me-1"></i> Buat Akun Baru
            </a>
        </div>
    </div>

    @if(session('success'))
        <div class="alert alert-success">{{ session('success') }}</div>
    @endif
    @if(session('error'))
        <div class="alert alert-danger">{{ session('error') }}</div>
    @endif

    <div class="card shadow-sm border-0">
        <div class="card-body p-0">
            @if(count($parsedUsers) > 0)
            <div class="table-responsive">
                <table class="table table-hover table-borderless align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th class="ps-4">Username</th>
                            <th>Masa Aktif</th>
                            <th class="text-end pe-4">Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($parsedUsers as $user)
                        <tr>
                            <td class="ps-4 fw-bold text-primary">{{ $user['username'] }}</td>
                            <td><span class="badge bg-secondary">{{ $user['expired'] ?? '-' }}</span></td>
                            <td class="text-end pe-4">
                                <form action="{{ route('vpn.suspend', [$protocol, $user['username']]) }}" method="POST" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-warning" title="Suspend">
                                        <i class="fas fa-pause"></i>
                                    </button>
                                </form>
                                <form action="{{ route('vpn.unsuspend', [$protocol, $user['username']]) }}" method="POST" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-success" title="Unsuspend">
                                        <i class="fas fa-play"></i>
                                    </button>
                                </form>
                                <a href="{{ route('vpn.renew', [$protocol, $user['username']]) }}" class="btn btn-sm btn-outline-info" title="Renew">
                                    <i class="fas fa-sync"></i>
                                </a>
                                <form action="{{ route('vpn.delete', [$protocol, $user['username']]) }}" method="POST" class="d-inline" onsubmit="return confirm('Hapus akun {{ $user['username'] }}?');">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-danger" title="Hapus">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </form>
                            </td>
                        </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
            @else
            <div class="p-5 text-center">
                <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Tidak ada akun yang ditemukan.</h5>
                <p class="text-muted small">Jika daftar ini tidak sesuai, cek raw output di bawah.</p>
            </div>
            @endif
        </div>
    </div>

    <!-- Raw Output Fallback -->
    <div class="card shadow-sm border-0 mt-4">
        <div class="card-header bg-white border-0 pt-4 pb-0">
            <h5 class="fw-bold mb-0"><i class="fas fa-terminal me-2"></i> Raw Output Server</h5>
        </div>
        <div class="card-body p-4">
            <pre class="bg-dark text-light p-3 rounded" style="max-height: 300px; overflow-y: auto;">{{ $rawList ?: 'Tidak ada output.' }}</pre>
        </div>
    </div>
</div>
@endsection
