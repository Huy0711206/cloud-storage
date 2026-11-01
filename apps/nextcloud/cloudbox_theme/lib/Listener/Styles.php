<?php
declare(strict_types=1);
namespace OCA\CloudboxTheme\Listener;
use OCP\EventDispatcher\Event;
use OCP\EventDispatcher\IEventListener;
use OCP\AppFramework\Http\Events\BeforeTemplateRenderedEvent;
use OCP\AppFramework\Http\Events\BeforeLoginTemplateRenderedEvent;
use OCP\Util;
use OCP\IConfig;
use OCP\IUserSession;
use OCA\CloudboxTheme\AppInfo\Application;
/** @implements IEventListener<BeforeTemplateRenderedEvent> */
class Styles implements IEventListener {
 public function __construct(private IConfig $config, private IUserSession $session) {}
 public function handle(Event $event): void {
  if ($event instanceof BeforeTemplateRenderedEvent || $event instanceof BeforeLoginTemplateRenderedEvent) { $path = __DIR__ . '/../../css/manifest.json';
   $manifest = is_file($path) ? (json_decode(file_get_contents($path), true) ?? []) : [];
   $style = $manifest['style'] ?? 'cloudbox';
   Util::addStyle(Application::APP_ID, $style);
   $user = $this->session->getUser();
   if ($user !== null && $this->config->getUserValue($user->getUID(), 'theming', 'background_image', 'default') !== 'default') { Util::addStyle(Application::APP_ID, $manifest['personal'] ?? 'personal'); } }
 }
}
