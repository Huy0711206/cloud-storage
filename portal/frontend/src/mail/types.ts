export interface MailAddress { Name: string; Address: string }
export interface MailPart {
  PartID: string; FileName: string; ContentType: string; ContentID: string; Size: number
  Checksums?: Record<string, string>
}
export interface MailSummary {
  ID: string; MessageID: string; Read: boolean; From: MailAddress
  To: MailAddress[]; Cc: MailAddress[]; Bcc: MailAddress[]
  Created: string; Subject: string; Size: number; Snippet: string
  Attachments: number; Tags: string[]
}
export interface MailDetail {
  ID: string; MessageID: string; From: MailAddress; To: MailAddress[]
  Cc: MailAddress[]; Bcc: MailAddress[]; ReplyTo: MailAddress[]
  Date: string; Subject: string; Text: string; HTML: string; Size: number
  Attachments: MailPart[]; Inline: MailPart[]; Tags: string[]; ReturnPath: string
}
export interface MailList {
  total: number; unread: number; count: number; messages_count: number
  messages_unread: number; start: number; tags: string[]; messages: MailSummary[]
}
