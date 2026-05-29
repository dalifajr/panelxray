@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0 text-white">Pusat Notifikasi</h2>
        <form action="{{ route('notifications.read-all') }}" method="POST">
            @csrf
            <button type="submit" class="btn btn-primary"><i class="fas fa-check-double me-2"></i>Tandai Semua Dibaca</button>
        </form>
    </div>

    @if(Auth::user()->role === 'admin')
    <div class="card border-0 shadow-sm lift-hover mb-4">
        <div class="card-header bg-dark text-white border-bottom border-secondary">
            <h5 class="mb-0"><i class="fas fa-broadcast-tower text-warning me-2"></i>Kirim Pengumuman Global</h5>
        </div>
        <div class="card-body bg-dark text-white">
            <form action="{{ route('admin.notifications.broadcast') }}" method="POST">
                @csrf
                <div class="mb-3">
                    <label class="form-label">Pesan Pengumuman</label>
                    <textarea name="message" rows="3" class="form-control bg-dark text-white border-secondary" required placeholder="Tulis pengumuman untuk seluruh customer di sini..."></textarea>
                </div>
                <button type="submit" class="btn btn-warning text-dark"><i class="fas fa-paper-plane me-2"></i>Kirim Broadast</button>
            </form>
        </div>
    </div>
    @endif

    <div class="card border-0 shadow-sm lift-hover">
        <div class="card-body bg-dark p-0">
            <ul class="list-group list-group-flush">
                @forelse($notifications as $notif)
                <li class="list-group-item bg-dark {{ $notif->is_read ? 'text-secondary' : 'text-white border-start border-primary border-4' }} border-secondary">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="d-flex gap-3">
                            <div class="mt-1">
                                @if($notif->type == 'system')
                                <i class="fas fa-cogs text-info fs-5"></i>
                                @elseif($notif->type == 'order')
                                <i class="fas fa-shopping-cart text-success fs-5"></i>
                                @elseif($notif->type == 'broadcast')
                                <i class="fas fa-bullhorn text-warning fs-5"></i>
                                @else
                                <i class="fas fa-bell text-primary fs-5"></i>
                                @endif
                            </div>
                            <div>
                                <div class="{{ $notif->is_read ? '' : 'fw-bold' }}">{{ $notif->message }}</div>
                                <div class="small text-secondary mt-1">{{ $notif->created_at->diffForHumans() }}</div>
                            </div>
                        </div>
                        @if(!$notif->is_read)
                        <span class="badge bg-primary rounded-pill">Baru</span>
                        @endif
                    </div>
                </li>
                @empty
                <li class="list-group-item bg-dark text-center py-5 border-secondary">
                    <i class="fas fa-bell-slash fs-1 text-secondary mb-3"></i>
                    <div class="text-secondary">Tidak ada notifikasi saat ini.</div>
                </li>
                @endforelse
            </ul>
        </div>
        @if($notifications->hasPages())
        <div class="card-footer bg-dark border-secondary">
            {{ $notifications->links() }}
        </div>
        @endif
    </div>
</div>
@endsection
