<?php
declare(strict_types=1);
namespace OCA\CloudboxTheme\AppInfo;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
use OCP\AppFramework\Http\Events\BeforeTemplateRenderedEvent;
use OCP\AppFramework\Http\Events\BeforeLoginTemplateRenderedEvent;
use OCA\CloudboxTheme\Listener\Styles;
class Application extends App implements IBootstrap {
 public const APP_ID = 'cloudbox_theme';
 public function __construct() { parent::__construct(self::APP_ID); }
 public function register(IRegistrationContext $context): void { $context->registerEventListener(BeforeTemplateRenderedEvent::class, Styles::class); $context->registerEventListener(BeforeLoginTemplateRenderedEvent::class, Styles::class); }
 public function boot(IBootContext $context): void {}
}
