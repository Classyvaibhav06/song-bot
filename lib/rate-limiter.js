/**
 * Simple in-memory rate limiter to prevent spam and avoid Instagram account flags/bans.
 */
class RateLimiter {
  constructor(limitPerHour) {
    this.limitPerHour = limitPerHour;
    // Map to store senderId/threadId -> array of timestamps
    this.timestamps = new Map();
  }

  /**
   * Checks if a command can be executed for the given identifier.
   * @param {string} identifier - User ID or Thread ID
   * @returns {boolean} - True if allowed, false if rate-limited
   */
  isAllowed(identifier) {
    const now = Date.now();
    const oneHourAgo = now - 60 * 60 * 1000;

    // Get existing timestamps or initialize empty array
    let userLogs = this.timestamps.get(identifier) || [];

    // Filter out logs older than 1 hour (rolling window)
    userLogs = userLogs.filter(timestamp => timestamp > oneHourAgo);

    // Check if limit is exceeded
    if (userLogs.length >= this.limitPerHour) {
      this.timestamps.set(identifier, userLogs); // update filtered list
      return false;
    }

    // Add current timestamp and save
    userLogs.push(now);
    this.timestamps.set(identifier, userLogs);
    return true;
  }

  /**
   * Gets the remaining requests allowed for an identifier in the current window.
   * @param {string} identifier
   * @returns {number}
   */
  getRemaining(identifier) {
    const now = Date.now();
    const oneHourAgo = now - 60 * 60 * 1000;
    const userLogs = (this.timestamps.get(identifier) || []).filter(timestamp => timestamp > oneHourAgo);
    return Math.max(0, this.limitPerHour - userLogs.length);
  }
}

module.exports = RateLimiter;
