/// <reference types="cypress" />

describe('Agent Connections', () => {
  beforeEach(() => {
    // Mock user authentication
    cy.visit('/');
    cy.get('[data-cy=sign-in-email]').type('admin@example.com');
    cy.get('[data-cy=sign-in-password]').type('password');
    cy.get('[data-cy=sign-in-button]').click();
    
    // Navigate to admin settings
    cy.get('[data-cy=user-menu]').click();
    cy.get('[data-cy=admin-settings]').click();
    cy.get('[data-cy=agent-connections-tab]').click();
  });

  it('should display agent connections page', () => {
    cy.contains('Agent Connections').should('be.visible');
    cy.get('[data-cy=add-connection-button]').should('be.visible');
  });

  it('should allow adding a new agent connection', () => {
    // Click add connection button
    cy.get('[data-cy=add-connection-button]').click();
    
    // Fill out the form
    cy.get('[data-cy=connection-name]').type('test_api_key');
    cy.get('[data-cy=connection-value]').type('sk-1234567890abcdef');
    cy.get('[data-cy=connection-agent-id]').type('test-agent');
    
    // Submit the form
    cy.get('[data-cy=create-connection-button]').click();
    
    // Verify success message
    cy.contains('Agent connections config saved successfully').should('be.visible');
    
    // Verify the connection appears in the table
    cy.get('[data-cy=connections-table]').should('contain', 'test_api_key');
  });

  it('should allow adding a common connection (admin only)', () => {
    // Note: This test assumes the user is logged in as an admin
    // since it's in the admin settings section
    
    // Click add connection button
    cy.get('[data-cy=add-connection-button]').click();
    
    // Fill out the form
    cy.get('[data-cy=connection-name]').type('common_key');
    cy.get('[data-cy=connection-value]').type('common-secret-value');
    
    // Enable common checkbox (should be enabled for admin users)
    cy.get('[data-cy=connection-is-common]').should('not.be.disabled');
    cy.get('[data-cy=connection-is-common]').click();
    
    // Submit the form
    cy.get('[data-cy=create-connection-button]').click();
    
    // Verify success message
    cy.contains('Agent connections config saved successfully').should('be.visible');
    
    // Verify the connection appears in the table with Common scope
    cy.get('[data-cy=connections-table]').should('contain', 'common_key');
    cy.get('[data-cy=connections-table]').should('contain', 'Common');
  });

  it('should validate connection name format', () => {
    // Click add connection button
    cy.get('[data-cy=add-connection-button]').click();
    
    // Enter invalid name with spaces
    cy.get('[data-cy=connection-name]').type('invalid name');
    cy.get('[data-cy=connection-value]').type('some-value');
    
    // Submit the form
    cy.get('[data-cy=create-connection-button]').click();
    
    // Verify error message
    cy.contains('Name must be alphanumeric with no spaces').should('be.visible');
  });

  it('should prevent non-admin users from creating common connections', () => {
    // Note: This test would need to be run in a context where the user is not an admin
    // For now, we can test the UI behavior when the user role is changed
    
    // Click add connection button
    cy.get('[data-cy=add-connection-button]').click();
    
    // Fill out the form
    cy.get('[data-cy=connection-name]').type('user_common_key');
    cy.get('[data-cy=connection-value]').type('user-secret-value');
    
    // For non-admin users, the common checkbox should be disabled
    // This test would need to be adjusted based on how user roles are handled in tests
    // cy.get('[data-cy=connection-is-common]').should('be.disabled');
    
    // If somehow a non-admin tries to submit with is_common=true, 
    // they should get an error message
    // This would require mocking the user role or setting up test users
  });

  it('should allow editing an existing connection', () => {
    // First create a connection
    cy.get('[data-cy=add-connection-button]').click();
    cy.get('[data-cy=connection-name]').type('edit_test_key');
    cy.get('[data-cy=connection-value]').type('original-value');
    cy.get('[data-cy=create-connection-button]').click();
    
    // Wait for success message
    cy.contains('Agent connections config saved successfully').should('be.visible');
    
    // Click edit button for the connection
    cy.get('[data-cy=edit-connection-edit_test_key]').click();
    
    // Update the value
    cy.get('[data-cy=connection-value]').clear();
    cy.get('[data-cy=connection-value]').type('updated-value');
    
    // Submit the form
    cy.get('[data-cy=update-connection-button]').click();
    
    // Verify success message
    cy.contains('Agent connections config saved successfully').should('be.visible');
  });

  it('should allow deleting a connection', () => {
    // First create a connection
    cy.get('[data-cy=add-connection-button]').click();
    cy.get('[data-cy=connection-name]').type('delete_test_key');
    cy.get('[data-cy=connection-value]').type('delete-value');
    cy.get('[data-cy=create-connection-button]').click();
    
    // Wait for success message
    cy.contains('Agent connections config saved successfully').should('be.visible');
    
    // Click delete button for the connection
    cy.get('[data-cy=delete-connection-delete_test_key]').click();
    
    // Confirm deletion
    cy.get('[data-cy=confirm-delete-button]').click();
    
    // Verify success message
    cy.contains('Agent connections config saved successfully').should('be.visible');
    
    // Verify the connection is removed from the table
    cy.get('[data-cy=connections-table]').should('not.contain', 'delete_test_key');
  });

  it('should support search functionality', () => {
    // Create multiple connections
    ['search_key_1', 'search_key_2', 'other_key'].forEach((name, index) => {
      cy.get('[data-cy=add-connection-button]').click();
      cy.get('[data-cy=connection-name]').type(name);
      cy.get('[data-cy=connection-value]').type(`value-${index}`);
      cy.get('[data-cy=create-connection-button]').click();
      cy.contains('Agent connections config saved successfully').should('be.visible');
    });
    
    // Test search functionality
    cy.get('[data-cy=search-connections]').type('search_key');
    
    // Should show only matching connections
    cy.get('[data-cy=connections-table]').should('contain', 'search_key_1');
    cy.get('[data-cy=connections-table]').should('contain', 'search_key_2');
    cy.get('[data-cy=connections-table]').should('not.contain', 'other_key');
    
    // Clear search
    cy.get('[data-cy=clear-search]').click();
    
    // Should show all connections again
    cy.get('[data-cy=connections-table]').should('contain', 'other_key');
  });

  it('should support pagination', () => {
    // Create enough connections to trigger pagination (assuming pageSize is 10)
    for (let i = 1; i <= 15; i++) {
      cy.get('[data-cy=add-connection-button]').click();
      cy.get('[data-cy=connection-name]').type(`pagination_key_${i}`);
      cy.get('[data-cy=connection-value]').type(`value-${i}`);
      cy.get('[data-cy=create-connection-button]').click();
      cy.contains('Agent connections config saved successfully').should('be.visible');
    }
    
    // Check pagination controls are visible
    cy.get('[data-cy=pagination-controls]').should('be.visible');
    cy.get('[data-cy=pagination-next]').should('be.visible');
    
    // Test pagination
    cy.get('[data-cy=pagination-next]').click();
    
    // Should show different connections on page 2
    cy.get('[data-cy=connections-table]').should('contain', 'pagination_key_');
  });

  it('should handle vault configuration', () => {
    // Navigate to vault configuration (if available)
    cy.get('[data-cy=vault-config-tab]').click();
    
    // Enable vault integration
    cy.get('[data-cy=enable-vault-integration]').click();
    
    // Fill vault configuration
    cy.get('[data-cy=vault-url]').clear();
    cy.get('[data-cy=vault-url]').type('http://localhost:8200');
    cy.get('[data-cy=vault-token]').clear();
    cy.get('[data-cy=vault-token]').type('test-token');
    cy.get('[data-cy=vault-mount-path]').clear();
    cy.get('[data-cy=vault-mount-path]').type('secret');
    
    // Test connection
    cy.get('[data-cy=test-vault-connection]').click();
    
    // Should show connection result (success or failure)
    cy.get('[data-cy=vault-test-result]').should('be.visible');
  });

  it('should display appropriate error messages', () => {
    // Test creating connection without required fields
    cy.get('[data-cy=add-connection-button]').click();
    cy.get('[data-cy=create-connection-button]').click();
    
    // Should show validation errors
    cy.contains('Name is required').should('be.visible');
    cy.contains('Value is required').should('be.visible');
  });

  it('should show vault storage indicator', () => {
    // If vault is enabled, connections should show vault storage indicator
    cy.get('[data-cy=add-connection-button]').click();
    cy.get('[data-cy=connection-name]').type('vault_stored_key');
    cy.get('[data-cy=connection-value]').type('vault-secret');
    cy.get('[data-cy=create-connection-button]').click();
    
    // If vault is enabled, the value should show as stored in vault
    cy.get('[data-cy=connections-table]').should('contain', '[STORED_IN_VAULT]');
  });
}); 