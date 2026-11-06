import { agentVideo } from '../../lib/agentMeta'

/** Vertical 30s explainer. Captions are burned into the video; the VTT track is
 * there for assistive tech and players that read it, so it isn't on by default. */
export default function AgentVideo({ agentId, title }: { agentId: string; title: string }) {
  const v = agentVideo(agentId)
  if (!v) return null
  return (
    <div className="agent-video">
      <video controls playsInline preload="none" poster={v.poster} aria-label={`30-second video: ${title}`}>
        <source src={v.src} type="video/mp4" />
        <track kind="captions" src={v.captions} srcLang="en" label="English" />
      </video>
    </div>
  )
}
