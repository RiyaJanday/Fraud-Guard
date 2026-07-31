export default function GradientBlobs({ variant = 'default' }) {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div
        className="absolute -top-40 -left-32 h-[32rem] w-[32rem] rounded-full bg-primary/30 blur-[120px] animate-blob-move"
        aria-hidden
      />
      <div
        className="absolute top-1/3 -right-40 h-[28rem] w-[28rem] rounded-full bg-accent/20 blur-[120px] animate-blob-move-2"
        aria-hidden
      />
      <div
        className="absolute bottom-0 left-1/4 h-[26rem] w-[26rem] rounded-full bg-secondary/25 blur-[130px] animate-blob-move"
        style={{ animationDelay: '4s' }}
        aria-hidden
      />
      {variant === 'auth' && (
        <div
          className="absolute top-1/2 left-1/2 h-[40rem] w-[40rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[160px]"
          aria-hidden
        />
      )}
      <div className="absolute inset-0 bg-bg/40" />
    </div>
  )
}
